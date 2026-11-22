import ipaddress
import json
from urllib.parse import urlsplit

import httpx


class APIError(Exception):
    """A safe, user-displayable API error."""


def validate_base_url(base_url):
    """Validate an OpenAI-compatible API URL before attaching credentials."""
    if not isinstance(base_url, str) or not base_url or base_url != base_url.strip():
        raise APIError("The API endpoint URL is invalid.")

    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        # Accessing .port also validates malformed port values.
        parsed.port
    except ValueError:
        raise APIError("The API endpoint URL is invalid.") from None

    if (
        parsed.scheme not in ("https", "http")
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise APIError("The API endpoint URL is invalid.")

    if any(char.isspace() for char in base_url):
        raise APIError("The API endpoint URL is invalid.")

    if parsed.scheme == "http":
        host = hostname.rstrip(".").lower()
        is_loopback = host == "localhost"
        try:
            is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass

        if not is_loopback:
            raise APIError(
                "Unencrypted HTTP is allowed only for localhost. Use HTTPS for remote APIs."
            )

    return base_url.rstrip("/")


MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_SSE_LINE_BYTES = 256 * 1024
MAX_MESSAGES = 100
MAX_MESSAGE_BYTES = 1024 * 1024


class OpenAICompatibleProvider:
    def __init__(self, base_url, api_key, model):
        self.base_url = validate_base_url(base_url)
        if not isinstance(api_key, str) or not api_key.strip():
            raise APIError("The API key is not configured.")
        if not isinstance(model, str) or not model.strip():
            raise APIError("The model name is not configured.")
        if len(model) > 256 or any(ord(char) < 32 for char in model):
            raise APIError("The model name is invalid.")

        self._api_key = api_key
        self.model = model.strip()

    def __repr__(self):
        return (
            "OpenAICompatibleProvider("
            f"base_url={self.base_url!r}, model={self.model!r}, "
            "api_key='[REDACTED]')"
        )

    def __str__(self):
        return repr(self)

    def get_endpoint(self):
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return self.base_url + "/chat/completions"

    @staticmethod
    def _prepare_payload(messages, model):
        if not isinstance(messages, list) or not messages or len(messages) > MAX_MESSAGES:
            raise APIError("The conversation contains an invalid number of messages.")

        for message in messages:
            if not isinstance(message, dict):
                raise APIError("The conversation contains an invalid message.")
            if message.get("role") not in ("system", "user", "assistant"):
                raise APIError("The conversation contains an unsupported message role.")
            content = message.get("content")
            if not isinstance(content, str):
                raise APIError("A conversation message is too large or invalid.")
            try:
                content_size = len(content.encode("utf-8"))
            except UnicodeError:
                raise APIError("A conversation message contains invalid text.") from None
            if content_size > MAX_MESSAGE_BYTES:
                raise APIError("A conversation message is too large or invalid.")

        payload = {"model": model, "messages": messages, "stream": True}
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError, UnicodeError):
            raise APIError("The conversation could not be encoded safely.") from None

        if len(body) > MAX_REQUEST_BYTES:
            raise APIError("The conversation is too large to send.")
        return body

    @staticmethod
    def _iter_content(response):
        total = 0
        buffer = bytearray()
        declared_length = response.headers.get("content-length")
        if declared_length and declared_length.isdigit() and int(declared_length) > MAX_RESPONSE_BYTES:
            raise APIError("The API response exceeded the size limit.")

        for chunk in response.iter_bytes(chunk_size=64 * 1024):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise APIError("The API response exceeded the size limit.")
            buffer.extend(chunk)

            while True:
                newline = buffer.find(b"\n")
                if newline < 0:
                    if len(buffer) > MAX_SSE_LINE_BYTES:
                        raise APIError("The API response contained an oversized event.")
                    break

                if newline > MAX_SSE_LINE_BYTES:
                    raise APIError("The API response contained an oversized event.")
                line = bytes(buffer[:newline]).rstrip(b"\r")
                del buffer[:newline + 1]

                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    return
                try:
                    event = json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                if not isinstance(event, dict):
                    continue
                choices = event.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                first_choice = choices[0]
                if not isinstance(first_choice, dict):
                    continue
                delta = first_choice.get("delta")
                if not isinstance(delta, dict):
                    continue
                content = delta.get("content")
                if isinstance(content, str):
                    yield content

        if buffer and len(buffer) > MAX_SSE_LINE_BYTES:
            raise APIError("The API response contained an oversized event.")

    def chat(self, messages):
        body = self._prepare_payload(messages, self.model)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        timeout = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=10.0)

        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    "POST",
                    self.get_endpoint(),
                    headers=headers,
                    content=body,
                ) as response:
                    if response.status_code >= 400:
                        raise APIError(f"The API returned HTTP {response.status_code}.")
                    yield from self._iter_content(response)

        except APIError:
            raise
        except httpx.TimeoutException:
            raise APIError("The API request timed out.") from None
        except httpx.HTTPError:
            raise APIError("A network error occurred while contacting the API.") from None
