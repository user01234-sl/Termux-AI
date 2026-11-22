import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from termuxai.core import config, history
from termuxai.security import secrets
from termuxai.models import manager
from termuxai.providers import offline
from termuxai.ui.safe_output import safe_terminal_text


class SafeTerminalOutputTests(unittest.TestCase):
    def test_strips_ansi_controls_and_bidi_overrides(self):
        value = "hello\x1b[31mRED\x1b[0m\u202eabc"
        self.assertEqual(safe_terminal_text(value), "hello[31mRED[0mabc")


class SymlinkProtectionTests(unittest.TestCase):
    def test_secret_reader_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_text('{"api_key":"must-not-be-read"}')
            link = root / "termuxai" / "secrets.json"
            link.parent.mkdir()
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable on this platform")
            with patch.object(secrets, "SECRETS_FILE", link):
                self.assertEqual(secrets.get_api_key(), "")
            self.assertIn("must-not-be-read", target.read_text())

    def test_config_reader_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_dir = root / "termuxai"
            app_dir.mkdir()
            target = root / "target.json"
            target.write_text('{"default_mode":"offline"}')
            config_file = app_dir / "settings.json"
            try:
                config_file.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable on this platform")
            with patch.object(config, "APP_DIR", app_dir), patch.object(config, "CONFIG_FILE", config_file):
                settings = config.load_config()
            self.assertEqual(settings["default_mode"], "online")
            self.assertEqual(target.read_text(), '{"default_mode":"offline"}')

    def test_history_database_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "termuxai"
            data_dir.mkdir()
            target = root / "target.db"
            target.write_bytes(b"not a database")
            db_file = data_dir / "history.db"
            try:
                db_file.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable on this platform")
            with patch.object(history, "DATA_DIR", data_dir), patch.object(history, "DB_FILE", db_file):
                with self.assertRaises(OSError):
                    history.get_connection()
            self.assertEqual(target.read_bytes(), b"not a database")


    def test_server_log_refuses_symlink_without_truncating_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "important.txt"
            target.write_text("keep this content")
            log_path = root / "termuxai" / "llama-server.log"
            log_path.parent.mkdir()
            try:
                log_path.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable on this platform")
            with patch.object(offline, "SERVER_LOG", log_path):
                with self.assertRaises(OSError):
                    offline._open_secure_server_log()
            self.assertEqual(target.read_text(), "keep this content")

    def test_model_catalog_reader_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            models_dir = data_dir / "models"
            models_dir.mkdir(parents=True)
            target = root / "external.json"
            target.write_text('{"active_model":null,"models":[]}')
            catalog = data_dir / "models.json"
            try:
                catalog.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable on this platform")
            patches = [
                patch.object(manager, "DATA_DIR", data_dir),
                patch.object(manager, "MODEL_DIR", models_dir),
                patch.object(manager, "CATALOG_FILE", catalog),
            ]
            for item in patches:
                item.start()
            try:
                with self.assertRaises(RuntimeError):
                    manager.load_catalog()
            finally:
                for item in reversed(patches):
                    item.stop()
            self.assertEqual(target.read_text(), '{"active_model":null,"models":[]}')


class ConfigValidationTests(unittest.TestCase):
    def test_invalid_mode_and_oversized_fields_are_rejected(self):
        settings = config._validated_settings({
            "default_mode": "[red]fake[/]",
            "api_base_url": "x" * 2049,
            "api_model": "m" * 257,
            "save_history": "yes",
        })
        self.assertEqual(settings["default_mode"], "online")
        self.assertEqual(settings["api_base_url"], "")
        self.assertEqual(settings["api_model"], "")
        self.assertIs(settings["save_history"], True)


if __name__ == "__main__":
    unittest.main()
