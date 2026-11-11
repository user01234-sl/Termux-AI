import json
import httpx


class APIError(Exception):
    pass


class OpenAICompatibleProvider:

    def __init__(self, base_url, api_key, model):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def get_endpoint(self):
        if self.base_url.endswith("/chat/completions"):
            return self.base_url

        return self.base_url + "/chat/completions"

    def chat(self, messages):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        try:
            with httpx.Client(timeout=90) as client:
                with client.stream(
                    "POST",
                    self.get_endpoint(),
                    headers=headers,
                    json=payload
                ) as response:

                    if response.status_code >= 400:
                        body = response.read().decode(
                            "utf-8", errors="replace"
                        )
                        raise APIError(
                            f"HTTP {response.status_code}: {body[:1000]}"
                        )

                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line[5:].strip()

                        if data == "[DONE]":
                            break

                        try:
                            event = json.loads(data)
                            choices = event.get("choices", [])

                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})
                            content = delta.get("content")

                            if isinstance(content, str):
                                yield content

                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            raise APIError("The API request timed out.")

        except httpx.ConnectError:
            raise APIError("Could not connect to the API endpoint.")

        except httpx.HTTPError as error:
            raise APIError(f"Network error: {error}")
