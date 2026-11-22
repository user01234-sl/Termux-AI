import hashlib
import unittest
from unittest.mock import patch

from termuxai.models import manager
from termuxai.providers.openai_compatible import (
    APIError,
    OpenAICompatibleProvider,
)


class FakeResponse:
    def __init__(self, body=b"GGUFdata", status_code=200, headers=None, url="https://models.example/model.gguf"):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {"content-length": str(len(body))}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def iter_bytes(self, chunk_size):
        yield self.body


class ModelIntegrityTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.models = base / "models"
        self.data = base / "data"
        self.catalog = self.data / "models.json"
        self.patches = [
            patch.object(manager, "MODEL_DIR", self.models),
            patch.object(manager, "DATA_DIR", self.data),
            patch.object(manager, "CATALOG_FILE", self.catalog),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_rejects_malformed_https_url(self):
        for url in (
            "https://example.com:bad/model.gguf",
            "https://example.com/a model.gguf",
            "https://user:pass@example.com/model.gguf",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                manager.validate_download_url(url)

    def test_download_accepts_matching_sha256(self):
        body = b"GGUFdata"

        class FakeClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def stream(self, method, url, **kwargs):
                return FakeResponse(body=body, url=url)

        with patch.object(manager.httpx, "Client", FakeClient):
            item = manager.download_model(
                "https://models.example/model.gguf",
                "model.gguf",
                expected_sha256=hashlib.sha256(body).hexdigest(),
            )
        self.assertEqual((self.models / "model.gguf").read_bytes(), body)
        self.assertEqual(item["filename"], "model.gguf")

    def test_download_rejects_sha256_mismatch_and_leaves_no_model(self):
        class FakeClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def stream(self, method, url, **kwargs):
                return FakeResponse(url=url)

        with patch.object(manager.httpx, "Client", FakeClient):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                manager.download_model(
                    "https://models.example/model.gguf",
                    "model.gguf",
                    expected_sha256="0" * 64,
                )
        self.assertFalse((self.models / "model.gguf").exists())
        self.assertEqual(list(self.models.glob("*.part")), [])

    def test_download_rejects_invalid_gguf_header(self):
        class FakeClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def stream(self, method, url, **kwargs):
                return FakeResponse(body=b"HTML error", url=url)

        with patch.object(manager.httpx, "Client", FakeClient):
            with self.assertRaisesRegex(ValueError, "GGUF header"):
                manager.download_model(
                    "https://models.example/model.gguf", "model.gguf"
                )
        self.assertFalse((self.models / "model.gguf").exists())

    def test_download_rejects_partial_http_response(self):
        class FakeClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def stream(self, method, url, **kwargs):
                return FakeResponse(status_code=206, url=url)

        with patch.object(manager.httpx, "Client", FakeClient):
            with self.assertRaisesRegex(ValueError, "unexpected HTTP status"):
                manager.download_model(
                    "https://models.example/model.gguf", "model.gguf"
                )
        self.assertFalse((self.models / "model.gguf").exists())

    def test_download_redirect_to_http_is_rejected(self):
        class RedirectResponse(FakeResponse):
            def __init__(self):
                super().__init__(status_code=302, headers={"location": "http://bad.example/model.gguf"})

        class FakeClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def stream(self, method, url, **kwargs):
                return RedirectResponse()

        with patch.object(manager.httpx, "Client", FakeClient):
            with self.assertRaises(ValueError):
                manager.download_model(
                    "https://models.example/model.gguf", "model.gguf"
                )

    def test_catalog_ignores_symlinked_model_file(self):
        from pathlib import Path
        self.models.mkdir(parents=True)
        outside = Path(self.temp.name) / "outside.gguf"
        outside.write_bytes(b"GGUF external")
        managed_link = self.models / "linked.gguf"
        try:
            managed_link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this platform")
        manager.save_catalog({
            "active_model": "linked-id",
            "models": [{
                "id": "linked-id",
                "name": "Linked",
                "filename": "linked.gguf",
            }],
        })
        self.assertEqual(manager.load_catalog()["models"], [])
        self.assertEqual(outside.read_bytes(), b"GGUF external")

    def test_import_rejects_invalid_gguf_magic(self):
        from pathlib import Path
        source = Path(self.temp.name) / "bad.gguf"
        source.write_bytes(b"NOPEnot a GGUF")
        with self.assertRaisesRegex(ValueError, "GGUF header"):
            manager.import_model(source)


class APIResourceLimitTests(unittest.TestCase):
    def setUp(self):
        self.provider = OpenAICompatibleProvider(
            "https://api.example/v1", "test-secret", "test-model"
        )

    def test_rejects_oversized_message_before_network_request(self):
        with self.assertRaises(APIError):
            self.provider._prepare_payload(
                [{"role": "user", "content": "x" * (1024 * 1024 + 1)}],
                "test-model",
            )

    def test_rejects_too_many_messages(self):
        messages = [{"role": "user", "content": "hello"}] * 101
        with self.assertRaises(APIError):
            self.provider._prepare_payload(messages, "test-model")

    def test_rejects_unsupported_message_role(self):
        with self.assertRaises(APIError):
            self.provider._prepare_payload(
                [{"role": "tool", "content": "not allowed"}],
                "test-model",
            )

    def test_parses_sse_content(self):
        class Response:
            headers = {}
            def iter_bytes(self, chunk_size):
                yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n'
                yield b'data: [DONE]\n'
        self.assertEqual(list(self.provider._iter_content(Response())), ["hello"])

    def test_rejects_oversized_response(self):
        class Response:
            headers = {}
            def iter_bytes(self, chunk_size):
                yield b"x" * 11
        with patch("termuxai.providers.openai_compatible.MAX_RESPONSE_BYTES", 10):
            with self.assertRaises(APIError):
                list(self.provider._iter_content(Response()))

    def test_rejects_oversized_sse_event(self):
        class Response:
            headers = {}
            def iter_bytes(self, chunk_size):
                yield b"x" * 11
        with patch("termuxai.providers.openai_compatible.MAX_SSE_LINE_BYTES", 10):
            with self.assertRaises(APIError):
                list(self.provider._iter_content(Response()))


if __name__ == "__main__":
    unittest.main()
