"""Private, atomic application configuration storage."""

import json
import os
import stat
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


def _validated_settings(data):
    """Accept only known settings with bounded, correctly typed values."""
    settings = DEFAULT_SETTINGS.copy()
    if not isinstance(data, dict):
        return settings

    for key in ("save_history", "show_timestamps"):
        if type(data.get(key)) is bool:
            settings[key] = data[key]

    if data.get("default_mode") in ("online", "offline"):
        settings["default_mode"] = data["default_mode"]

    endpoint = data.get("api_base_url")
    if isinstance(endpoint, str) and len(endpoint) <= 2048 and not any(ord(c) < 32 for c in endpoint):
        settings["api_base_url"] = endpoint.strip()

    model = data.get("api_model")
    if isinstance(model, str) and len(model) <= 256 and not any(ord(c) < 32 for c in model):
        settings["api_model"] = model.strip()

    return settings


def _secure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if APP_DIR.is_symlink() or not APP_DIR.is_dir():
        raise OSError("The configuration path must be a real directory.")
    os.chmod(APP_DIR, 0o700)


def _read_config():
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    elif CONFIG_FILE.is_symlink():
        raise OSError("The configuration file must not be a symbolic link.")
    fd = os.open(str(CONFIG_FILE), flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("The configuration file is not a regular file.")
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "r", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise


def load_config():
    try:
        _secure_app_dir()
    except OSError:
        print("Warning: The configuration directory is not secure.")
        print("Using default settings.")
        return DEFAULT_SETTINGS.copy()

    if not CONFIG_FILE.exists() and not CONFIG_FILE.is_symlink():
        save_config(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

    try:
        with _read_config() as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Configuration must be a JSON object")
        return _validated_settings(data)

    except (json.JSONDecodeError, OSError, ValueError):
        print("Warning: Could not safely load configuration.")
        print("Using default settings.")
        return DEFAULT_SETTINGS.copy()


def save_config(settings):
    _secure_app_dir()
    settings = _validated_settings(settings)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".settings-", suffix=".tmp", dir=str(APP_DIR)
    )
    temporary_file = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        # Atomic replacement does not follow a pre-existing destination symlink.
        os.replace(temporary_file, CONFIG_FILE)
        os.chmod(CONFIG_FILE, 0o600)
    finally:
        temporary_file.unlink(missing_ok=True)


def get_config_path():
    return CONFIG_FILE
