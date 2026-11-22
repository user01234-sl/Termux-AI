"""Owner-only storage for API credentials."""

import json
import os
import stat
import tempfile
from pathlib import Path
from getpass import getpass

SECRETS_FILE = Path.home() / ".config" / "termuxai" / "secrets.json"


def _secure_directory():
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SECRETS_FILE.parent.is_symlink() or not SECRETS_FILE.parent.is_dir():
        raise OSError("The secrets directory must be a real directory.")
    os.chmod(SECRETS_FILE.parent, 0o700)


def _open_secret_readonly():
    """Open the secret without following a final-component symlink."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    elif SECRETS_FILE.is_symlink():
        raise OSError("The secrets file must not be a symbolic link.")
    fd = os.open(str(SECRETS_FILE), flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("The secrets file is not a regular file.")
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "r", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise


def save_api_key(api_key):
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("API key cannot be empty.")

    _secure_directory()
    fd, temporary_name = tempfile.mkstemp(
        prefix=".secrets-", suffix=".tmp", dir=str(SECRETS_FILE.parent)
    )
    temporary_file = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump({"api_key": api_key.strip()}, file)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        # os.replace replaces a destination symlink itself; it does not follow it.
        os.replace(temporary_file, SECRETS_FILE)
        os.chmod(SECRETS_FILE, 0o600)
    finally:
        temporary_file.unlink(missing_ok=True)


def get_api_key():
    try:
        _secure_directory()
        if not SECRETS_FILE.exists() and not SECRETS_FILE.is_symlink():
            return ""
        with _open_secret_readonly() as file:
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
