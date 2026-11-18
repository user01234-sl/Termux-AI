import json
import os
import tempfile
from pathlib import Path


APP_DIR = Path.home() / ".config" / "termuxai"
CONFIG_FILE = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "app_name": "TermuxAI",
    "save_history": True,
    "show_timestamps": True,
    "default_mode": "online",
    "api_base_url": "",
    "api_model": ""
}


def _secure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(APP_DIR, 0o700)
    except OSError:
        pass


def load_config():
    _secure_app_dir()

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

    try:
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")

        settings = DEFAULT_SETTINGS.copy()
        for key in DEFAULT_SETTINGS:
            if key in data and type(data[key]) is type(DEFAULT_SETTINGS[key]):
                settings[key] = data[key]
        return settings

    except (json.JSONDecodeError, OSError, ValueError):
        print("Warning: Could not load configuration.")
        print("Using default settings.")
        return DEFAULT_SETTINGS.copy()


def save_config(settings):
    _secure_app_dir()
    fd, temporary_name = tempfile.mkstemp(
        prefix=".settings-", suffix=".tmp", dir=str(APP_DIR)
    )
    temporary_file = Path(temporary_name)

    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_file, CONFIG_FILE)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
    finally:
        try:
            temporary_file.unlink()
        except FileNotFoundError:
            pass


def get_config_path():
    return CONFIG_FILE
