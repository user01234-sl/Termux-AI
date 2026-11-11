import json
import os
from pathlib import Path
from getpass import getpass

SECRETS_FILE = Path.home() / ".config" / "termuxai" / "secrets.json"


def save_api_key(api_key):
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = SECRETS_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump({"api_key": api_key}, file)

    os.replace(temporary_file, SECRETS_FILE)

    try:
        os.chmod(SECRETS_FILE, 0o600)
    except OSError:
        pass


def get_api_key():
    try:
        with SECRETS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("api_key", "")

    except (OSError, json.JSONDecodeError):
        return ""


def prompt_for_api_key():
    api_key = getpass("Enter your API key (input hidden): ").strip()

    if not api_key:
        print("No API key entered.")
        return False

    save_api_key(api_key)
    print("API key saved.")
    return True


def delete_api_key():
    try:
        SECRETS_FILE.unlink()
        print("API key deleted.")
    except FileNotFoundError:
        print("No saved API key found.")
