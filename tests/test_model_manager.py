import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from termuxai.models import manager


class ModelManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.models = root / "models"
        self.data = root / "data"
        self.catalog = root / "data" / "models.json"
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

    def test_requires_https(self):
        for url in ("http://example.com/model.gguf", "file:///tmp/model.gguf", "https://user:pass@example.com/a.gguf"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                manager.validate_download_url(url)

    def test_rejects_bad_filename(self):
        for name in ("model.bin", ".gguf", "../model.bin"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                manager.safe_filename(name)

    def test_catalog_round_trip_and_active_model(self):
        self.models.mkdir(parents=True)
        (self.models / "demo.gguf").write_bytes(b"gguf")
        manager.save_catalog({"active_model": "demo-id", "models": [{
            "id": "demo-id", "name": "Demo", "filename": "demo.gguf",
            "context_size": 4096, "port": 8081, "threads": 4, "gpu_layers": 0,
        }]})
        catalog = manager.load_catalog()
        self.assertEqual(catalog["active_model"], "demo-id")
        self.assertEqual(catalog["models"][0]["context_size"], 4096)

    def test_rejects_out_of_range_startup_settings(self):
        self.models.mkdir(parents=True)
        (self.models / "demo.gguf").touch()
        manager.save_catalog({"active_model": "demo-id", "models": [{
            "id": "demo-id", "name": "Demo", "filename": "demo.gguf",
        }]})
        with self.assertRaises(ValueError):
            manager.update_model_settings("demo-id", port=80)


    def test_download_stream_registers_gguf_model(self):
        class FakeResponse:
            status_code = 200
            headers = {"content-length": "8"}
            url = "https://models.example/demo.gguf"
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def raise_for_status(self): pass
            def iter_bytes(self, chunk_size):
                yield b"GGUFdata"

        class FakeClient:
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def stream(self, *args, **kwargs): return FakeResponse()

        with patch.object(manager.httpx, "Client", FakeClient):
            item = manager.download_model("https://models.example/demo.gguf", "demo.gguf")
        self.assertEqual((self.models / "demo.gguf").read_bytes(), b"GGUFdata")
        catalog = manager.load_catalog()
        self.assertEqual(catalog["active_model"], item["id"])
        self.assertEqual(len(catalog["models"]), 1)


    def test_import_copies_and_registers_model_without_changing_original(self):
        source = Path(self.temp.name) / "outside" / "sample.gguf"
        source.parent.mkdir()
        source.write_bytes(b"GGUF model bytes")
        item = manager.import_model(source)
        managed = self.models / "sample.gguf"
        self.assertTrue(managed.is_file())
        self.assertEqual(managed.read_bytes(), b"GGUF model bytes")
        self.assertEqual(source.read_bytes(), b"GGUF model bytes")
        self.assertEqual(manager.load_catalog()["models"][0]["id"], item["id"])

    def test_import_rejects_non_gguf_and_missing_files(self):
        bad = Path(self.temp.name) / "model.bin"
        bad.write_bytes(b"not gguf")
        with self.assertRaises(ValueError):
            manager.import_model(bad)
        with self.assertRaises(ValueError):
            manager.import_model(Path(self.temp.name) / "missing.gguf")

    def test_import_rejects_duplicate_filename(self):
        source = Path(self.temp.name) / "source" / "same.gguf"
        source.parent.mkdir()
        source.write_bytes(b"GGUF")
        self.models.mkdir(parents=True)
        (self.models / "same.gguf").write_bytes(b"already here")
        with self.assertRaises(FileExistsError):
            manager.import_model(source)

    def test_delete_removes_model_and_catalog_entry(self):
        self.models.mkdir(parents=True)
        (self.models / "demo.gguf").touch()
        manager.save_catalog({"active_model": "demo-id", "models": [{
            "id": "demo-id", "name": "Demo", "filename": "demo.gguf",
        }]})
        manager.delete_model("demo-id")
        self.assertFalse((self.models / "demo.gguf").exists())
        self.assertEqual(manager.load_catalog()["models"], [])


if __name__ == "__main__":
    unittest.main()
