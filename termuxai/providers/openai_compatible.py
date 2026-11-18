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


class OpenAICompatibleProvider:
    def __init__(self, base_url, api_key, model):
        self.base_url = validate_base_url(base_url)
        if not isinstance(api_key, str) or not api_key.strip():
            raise APIError("The API key is not configured.")
        if not isinstance(model, str) or not model.strip():
            raise APIError("The model name is not configured.")

        # Keep the credential out of the default object representation. This
        # helps prevent accidental disclosure in tracebacks and debug output.
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

    def chat(self, messages):
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
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
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        # Do not print provider response bodies: they can contain
                        # account details, request data, or reflected credentials.
                        raise APIError(
                            f"The API returned HTTP {response.status_code}."
                        )

                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line[5:].strip()
                        if data == "[DONE]":
                            break

                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        if not isinstance(event, dict):
                            continue
                        choices = event.get("choices", [])
                        if not isinstance(choices, list) or not choices:
                            continue

                        first_choice = choices[0]
                        if not isinstance(first_choice, dict):
                            continue
                        delta = first_choice.get("delta", {})
                        if not isinstance(delta, dict):
                            continue
                        content = delta.get("content")
                        if isinstance(content, str):
                            yield content

        except APIError:
            raise
        except httpx.TimeoutException:
            raise APIError("The API request timed out.") from None
        except httpx.HTTPError:
            # Avoid displaying raw exceptions, which can include full URLs.
            raise APIError("A network error occurred while contacting the API.") from None
