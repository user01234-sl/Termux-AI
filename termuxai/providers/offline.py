import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx

from termuxai.models.manager import load_catalog, MODEL_DIR


SERVER_LOG = Path.home() / ".config" / "termuxai" / "llama-server.log"
STARTUP_TIMEOUT = 90


def server_is_running(port=8080):
    """Check whether a local llama.cpp server is responding."""
    server_url = f"http://127.0.0.1:{port}"

    try:
        health = httpx.get(
            f"{server_url}/health",
            timeout=2,
        )

        if health.status_code != 200:
            return False

        models = httpx.get(
            f"{server_url}/v1/models",
            timeout=2,
        )

        if models.status_code != 200:
            return False

        payload = models.json()

        return isinstance(payload.get("data"), list)

    except (httpx.RequestError, ValueError, AttributeError):
        return False


def get_model_path():
    """Return the active model's path from the model catalogue."""
    config = get_active_model_config()
    return Path(config["path"])


def _open_secure_server_log():
    """Open the server log with owner-only permissions."""
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.chmod(SERVER_LOG.parent, 0o700)
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    fd = os.open(str(SERVER_LOG), flags, 0o600)

    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            pass

        return os.fdopen(fd, "w", encoding="utf-8")

    except Exception:
        os.close(fd)
        raise


def get_active_model_config():
    """Get the currently selected model from models.json."""
    catalog = load_catalog()

    selected = next(
        (
            item
            for item in catalog["models"]
            if item["id"] == catalog["active_model"]
        ),
        None,
    )

    if selected is None:
        raise RuntimeError(
            "No active model found. Open Model Manager "
            "and import or download a GGUF model."
        )

    model_path = MODEL_DIR / selected["filename"]

    if not model_path.is_file():
        raise RuntimeError(
            f"Model file not found: {model_path}. "
            "Open Model Manager to check your model library."
        )

    return {
        "id": selected["id"],
        "name": selected["name"],
        "path": model_path,
        "context_size": selected["context_size"],
        "port": selected["port"],
        "threads": selected["threads"],
        "gpu_layers": selected["gpu_layers"],
    }


def start_server(model_config=None):
    """Start llama.cpp using the active model configuration."""
    model_config = model_config or get_active_model_config()

    port = model_config["port"]

    if server_is_running(port):
        return None

    llama_server = shutil.which("llama-server")

    if not llama_server:
        raise RuntimeError(
            "llama-server was not found. "
            "Install it with: pkg install llama-cpp"
        )

    model_path = Path(model_config["path"])

    if not model_path.is_file():
        raise RuntimeError(
            f"Model file not found: {model_path}"
        )

    command = [
        llama_server,
        "-m", str(model_path),
        "-c", str(model_config["context_size"]),
        "--host", "127.0.0.1",
        "--port", str(port),
    ]

    if model_config["threads"]:
        command.extend([
            "--threads",
            str(model_config["threads"]),
        ])

    if model_config["gpu_layers"]:
        command.extend([
            "--n-gpu-layers",
            str(model_config["gpu_layers"]),
        ])

    with _open_secure_server_log() as log_file:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    start_time = time.monotonic()

    while time.monotonic() - start_time < STARTUP_TIMEOUT:

        if process.poll() is not None:
            raise RuntimeError(
                "llama-server stopped unexpectedly. "
                f"Check the private diagnostic log: {SERVER_LOG}"
            )

        if server_is_running(port):
            return process

        time.sleep(1)

    process.terminate()

    try:
        process.wait(timeout=5)

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()

    raise RuntimeError(
        f"llama-server did not become ready within "
        f"{STARTUP_TIMEOUT} seconds. "
        f"Check {SERVER_LOG}"
    )


def stop_server(process):
    """Stop only the server started by this TermuxAI session."""
    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=10)

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
