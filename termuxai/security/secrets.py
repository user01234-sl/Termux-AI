import json
import os
import tempfile
from pathlib import Path
from getpass import getpass

SECRETS_FILE = Path.home() / ".config" / "termuxai" / "secrets.json"


def _secure_directory():
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SECRETS_FILE.parent, 0o700)
    except OSError:
        pass


def save_api_key(api_key):
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("API key cannot be empty.")

    _secure_directory()
    fd, temporary_name = tempfile.mkstemp(
        prefix=".secrets-", suffix=".tmp", dir=str(SECRETS_FILE.parent)
    )
    temporary_file = Path(temporary_name)

    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump({"api_key": api_key.strip()}, file)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_file, SECRETS_FILE)
        try:
            os.chmod(SECRETS_FILE, 0o600)
        except OSError:
            pass
    finally:
        try:
            temporary_file.unlink()
        except FileNotFoundError:
            pass


def get_api_key():
    try:
        _secure_directory()
        if not SECRETS_FILE.is_file():
            return ""
        try:
            os.chmod(SECRETS_FILE, 0o600)
        except OSError:
            pass

        with SECRETS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return ""
        key = data.get("api_key", "")
        return key if isinstance(key, str) else ""

    except (OSError, json.JSONDecodeError):
        return ""


def prompt_for_api_key():
    api_key = getpass("Enter your API key (input hidden): ").strip()
    if not api_key:
        print("No API key entered.")
        return False

    try:
        save_api_key(api_key)
    except (OSError, ValueError):
        print("Could not securely save the API key.")
        return False

    print("API key saved.")
    return True


def delete_api_key():
    try:
        SECRETS_FILE.unlink()
        print("API key deleted.")
    except FileNotFoundError:
        print("No saved API key found.")
    except OSError:
        print("Could not delete the saved API key.")
