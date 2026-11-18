import unittest
from pathlib import Path
from unittest.mock import patch

from termuxai.providers import offline


class ModelPathTests(unittest.TestCase):

    def setUp(self):
        self.model = {
            "id": "test-model",
            "name": "Test Model",
            "filename": "test-model.gguf",
            "context_size": 2048,
            "port": 8080,
            "threads": 4,
            "gpu_layers": 0,
        }

    @patch.object(offline, "load_catalog")
    @patch.object(offline, "MODEL_DIR")
    def test_returns_active_model_path(self, mock_model_dir, mock_catalog):
        mock_model_dir.__truediv__.return_value = Path(
            "/fake/models/test-model.gguf"
        )

        mock_catalog.return_value = {
            "active_model": "test-model",
            "models": [self.model],
        }

        with patch.object(
            offline.Path,
            "is_file",
            return_value=True
        ):
            config = offline.get_active_model_config()

        self.assertEqual(
            config["path"],
            Path("/fake/models/test-model.gguf")
        )
        self.assertEqual(config["name"], "Test Model")

    @patch.object(offline, "load_catalog")
    def test_raises_when_no_active_model(self, mock_catalog):
        mock_catalog.return_value = {
            "active_model": None,
            "models": [],
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "No active model found"
        ):
            offline.get_active_model_config()

    @patch.object(offline, "load_catalog")
    @patch.object(offline, "MODEL_DIR")
    def test_raises_when_model_file_is_missing(
        self,
        mock_model_dir,
        mock_catalog
    ):
        mock_model_dir.__truediv__.return_value = Path(
            "/fake/models/missing.gguf"
        )

        mock_catalog.return_value = {
            "active_model": "test-model",
            "models": [self.model],
        }

        with patch.object(
            offline.Path,
            "is_file",
            return_value=False
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Model file not found"
            ):
                offline.get_active_model_config()


if __name__ == "__main__":
    unittest.main()
