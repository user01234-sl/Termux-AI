"""Secure local GGUF model catalogue and downloader."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "termuxai"
MODEL_DIR = DATA_DIR / "models"
CATALOG_FILE = DATA_DIR / "models.json"
MAX_MODEL_BYTES = 20 * 1024 ** 3
CHUNK_SIZE = 1024 * 1024


def _secure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _atomic_json(path, data):
    _secure_dir(path.parent)
    fd, temp_name = tempfile.mkstemp(prefix=".models-", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        temp_path.unlink(missing_ok=True)


def load_catalog():
    _secure_dir(DATA_DIR)
    _secure_dir(MODEL_DIR)
    if not CATALOG_FILE.exists():
        return {"active_model": None, "models": []}
    try:
        with CATALOG_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            raise ValueError("Invalid model catalogue")
        valid = []
        for item in data["models"]:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            if not isinstance(filename, str) or Path(filename).name != filename or not filename.lower().endswith(".gguf"):
                continue
            path = MODEL_DIR / filename
            if path.is_file():
                valid.append({
                    "id": str(item.get("id", filename)),
                    "name": str(item.get("name", filename)),
                    "filename": filename,
                    "context_size": _valid_int(item.get("context_size"), 2048, 256, 131072),
                    "port": _valid_int(item.get("port"), 8080, 1024, 65535),
                    "threads": _valid_int(item.get("threads"), 0, 0, 256),
                    "gpu_layers": _valid_int(item.get("gpu_layers"), 0, 0, 999),
                })
        active = data.get("active_model")
        if active not in [m["id"] for m in valid]:
            active = valid[0]["id"] if valid else None
        return {"active_model": active, "models": valid}
    except (OSError, ValueError, json.JSONDecodeError):
        raise RuntimeError("The model catalogue could not be read. Check its JSON format and permissions.")


def save_catalog(catalog):
    _atomic_json(CATALOG_FILE, catalog)


def _valid_int(value, default, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        return default
    return value


def validate_download_url(url):
    if not isinstance(url, str) or len(url) > 8192:
        raise ValueError("Enter a valid HTTPS model URL.")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Model downloads require an HTTPS URL without embedded credentials.")
    if parsed.fragment:
        raise ValueError("URL fragments are not supported.")
    return url.strip()


def safe_filename(filename):
    name = Path(filename.strip()).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not name.lower().endswith(".gguf"):
        raise ValueError("The model filename must end with .gguf.")
    if name in ("", ".gguf") or name.startswith("."):
        raise ValueError("Choose a normal filename for the model.")
    return name



def _register_model(filename):
    """Register an already-present model file in the managed catalogue."""
    catalog = load_catalog()
    model_id = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:12]
    if any(item["id"] == model_id or item["filename"] == filename for item in catalog["models"]):
        raise FileExistsError("This model is already registered.")
    item = {
        "id": model_id,
        "name": Path(filename).stem,
        "filename": filename,
        "context_size": 2048,
        "port": 8080,
        "threads": 0,
        "gpu_layers": 0,
    }
    catalog["models"].append(item)
    if catalog["active_model"] is None:
        catalog["active_model"] = model_id
    save_catalog(catalog)
    return item


def import_model(source_path, progress_callback=None):
    """Copy an existing local GGUF file into TermuxAI and register it."""
    try:
        source = Path(source_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError("The selected model file could not be found.") from error
    if not source.is_file() or source.suffix.lower() != ".gguf":
        raise ValueError("Select an existing .gguf model file.")
    filename = safe_filename(source.name)
    size = source.stat().st_size
    if size <= 0:
        raise ValueError("The selected model file is empty.")
    if size > MAX_MODEL_BYTES:
        raise ValueError("The model exceeds the 20 GB import limit.")

    _secure_dir(MODEL_DIR)
    destination = MODEL_DIR / filename
    if destination.exists():
        raise FileExistsError("A model with that filename already exists in the library.")
    if source == destination.resolve(strict=False):
        raise ValueError("The model is already in the TermuxAI model directory.")

    fd, temp_name = tempfile.mkstemp(prefix=".import-", suffix=".part", dir=str(MODEL_DIR))
    temporary = Path(temp_name)
    copied = 0
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > MAX_MODEL_BYTES:
                    raise ValueError("The model exceeds the 20 GB import limit.")
                dst.write(chunk)
                if progress_callback:
                    progress_callback(copied, size)
            dst.flush()
            os.fsync(dst.fileno())
        if copied != size:
            raise ValueError("The model file changed during import; no model was added.")
        os.replace(temporary, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
        try:
            return _register_model(filename)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    finally:
        temporary.unlink(missing_ok=True)


def download_model(url, filename, progress_callback=None):
    url = validate_download_url(url)
    filename = safe_filename(filename)
    _secure_dir(MODEL_DIR)
    destination = MODEL_DIR / filename
    if destination.exists():
        raise FileExistsError("A model with that filename already exists.")
    temporary = MODEL_DIR / (filename + ".part")
    if temporary.exists():
        temporary.unlink()

    total = 0
    try:
        timeout = httpx.Timeout(connect=20, read=60, write=30, pool=10)
        with httpx.Client(timeout=timeout, follow_redirects=True, max_redirects=5, trust_env=False) as client:
            with client.stream("GET", url, headers={"User-Agent": "TermuxAI/0.3.5"}) as response:
                response.raise_for_status()
                final = urlsplit(str(response.url))
                if final.scheme != "https":
                    raise ValueError("The download redirected to a non-HTTPS address; download cancelled.")
                length = response.headers.get("content-length")
                expected = int(length) if length and length.isdigit() else None
                if expected is not None and expected > MAX_MODEL_BYTES:
                    raise ValueError("The model exceeds the 20 GB download limit.")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                fd = os.open(str(temporary), flags, 0o600)
                with os.fdopen(fd, "wb") as handle:
                    for chunk in response.iter_bytes(CHUNK_SIZE):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > MAX_MODEL_BYTES:
                            raise ValueError("The model exceeds the 20 GB download limit.")
                        handle.write(chunk)
                        if progress_callback:
                            progress_callback(total, expected)
                    handle.flush()
                    os.fsync(handle.fileno())
        if total == 0:
            raise ValueError("The server returned an empty file.")
        if expected is not None and total != expected:
            raise ValueError("The download was incomplete. The partial file was discarded.")
        os.replace(temporary, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    try:
        return _register_model(filename)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def update_model_settings(model_id, *, context_size=None, port=None, threads=None, gpu_layers=None):
    catalog = load_catalog()
    model = next((m for m in catalog["models"] if m["id"] == model_id), None)
    if model is None:
        raise ValueError("Model not found.")
    values = {
        "context_size": (context_size, 256, 131072),
        "port": (port, 1024, 65535),
        "threads": (threads, 0, 256),
        "gpu_layers": (gpu_layers, 0, 999),
    }
    for key, (value, low, high) in values.items():
        if value is not None:
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid {key.replace('_', ' ')} value.")
            model[key] = value
    save_catalog(catalog)
    return model


def set_active_model(model_id):
    catalog = load_catalog()
    if not any(m["id"] == model_id for m in catalog["models"]):
        raise ValueError("Model not found.")
    catalog["active_model"] = model_id
    save_catalog(catalog)


def delete_model(model_id):
    catalog = load_catalog()
    model = next((m for m in catalog["models"] if m["id"] == model_id), None)
    if model is None:
        raise ValueError("Model not found.")
    path = MODEL_DIR / model["filename"]
    if path.parent != MODEL_DIR or path.name != model["filename"]:
        raise ValueError("Invalid model path.")
    path.unlink(missing_ok=True)
    catalog["models"] = [m for m in catalog["models"] if m["id"] != model_id]
    catalog["active_model"] = catalog["models"][0]["id"] if catalog["models"] else None
    save_catalog(catalog)
