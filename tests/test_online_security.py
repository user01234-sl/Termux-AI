import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from termuxai.providers.openai_compatible import (
    APIError,
    OpenAICompatibleProvider,
    validate_base_url,
)
from termuxai.security import secrets
from termuxai.core import history
from termuxai.providers import offline


class EndpointSecurityTests(unittest.TestCase):
    def test_https_remote_endpoint_is_allowed(self):
        self.assertEqual(
            validate_base_url("https://api.example.com/v1/"),
            "https://api.example.com/v1",
        )

    def test_remote_http_is_rejected(self):
        with self.assertRaises(APIError):
            validate_base_url("http://api.example.com/v1")

    def test_loopback_http_is_allowed_for_local_servers(self):
        self.assertEqual(
            validate_base_url("http://127.0.0.1:8080/v1"),
            "http://127.0.0.1:8080/v1",
        )
        self.assertEqual(
            validate_base_url("http://localhost:8080/v1"),
            "http://localhost:8080/v1",
        )

    def test_credentials_query_and_fragment_are_rejected(self):
        bad_urls = [
            "https://user:pass@example.com/v1",
            "https://example.com/v1?token=secret",
            "https://example.com/v1#fragment",
        ]
        for url in bad_urls:
            with self.subTest(url=url):
                with self.assertRaises(APIError):
                    validate_base_url(url)

    def test_invalid_endpoint_does_not_construct_provider(self):
        with self.assertRaises(APIError):
            OpenAICompatibleProvider(
                "http://remote.example.com/v1", "fake-key", "model"
            )

    def test_provider_representation_never_displays_api_key(self):
        provider = OpenAICompatibleProvider(
            "https://api.example.com/v1", "very-secret-test-key", "test-model"
        )
        self.assertNotIn("very-secret-test-key", repr(provider))
        self.assertNotIn("very-secret-test-key", str(provider))
        self.assertIn("[REDACTED]", repr(provider))


class SecretStorageTests(unittest.TestCase):
    def test_secret_is_written_with_restricted_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_path = Path(directory) / "termuxai" / "secrets.json"
            with patch.object(secrets, "SECRETS_FILE", secret_path):
                secrets.save_api_key("test-key")
                self.assertEqual(secrets.get_api_key(), "test-key")
                if os.name == "posix":
                    self.assertEqual(secret_path.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(secret_path.parent.stat().st_mode & 0o777, 0o700)


class LocalLogPrivacyTests(unittest.TestCase):
    def test_local_server_log_uses_restricted_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "termuxai" / "llama-server.log"
            with patch.object(offline, "SERVER_LOG", log_path):
                with offline._open_secure_server_log() as log_file:
                    log_file.write("private diagnostic text")

                self.assertEqual(
                    log_path.read_text(encoding="utf-8"),
                    "private diagnostic text",
                )
                if os.name == "posix":
                    self.assertEqual(log_path.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(log_path.parent.stat().st_mode & 0o777, 0o700)


class HistoryPrivacyTests(unittest.TestCase):
    def test_history_directory_and_database_have_restricted_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "termuxai"
            db_file = data_dir / "history.db"
            with patch.object(history, "DATA_DIR", data_dir), \
                 patch.object(history, "DB_FILE", db_file):
                history.init_db()
                if os.name == "posix":
                    self.assertEqual(data_dir.stat().st_mode & 0o777, 0o700)
                    self.assertEqual(db_file.stat().st_mode & 0o777, 0o600)

    def test_clear_history_removes_conversations_and_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "termuxai"
            db_file = data_dir / "history.db"
            with patch.object(history, "DATA_DIR", data_dir), \
                 patch.object(history, "DB_FILE", db_file):
                chat_id = history.create_conversation("online")
                history.add_message(chat_id, "user", "private message")
                history.clear_history()
                self.assertEqual(history.get_conversations(), [])
                conversation, messages = history.get_conversation(chat_id)
                self.assertIsNone(conversation)
                self.assertEqual(messages, [])


if __name__ == "__main__":
    unittest.main()
