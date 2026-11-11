import json
import os
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


def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")

        settings = DEFAULT_SETTINGS.copy()

        for key in DEFAULT_SETTINGS:
            if key in data and type(data[key]) is type(DEFAULT_SETTINGS[key]):
                settings[key] = data[key]

        return settings

    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Warning: Could not load configuration: {error}")
        print("Using default settings.")
        return DEFAULT_SETTINGS.copy()


def save_config(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = CONFIG_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)
        file.write("\n")

    os.replace(temporary_file, CONFIG_FILE)

    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def get_config_path():
    return CONFIG_FILE