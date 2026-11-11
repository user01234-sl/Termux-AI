import shutil
import subprocess
import time
from pathlib import Path

import httpx


PROJECT_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = (
    PROJECT_DIR
    / "models"
    / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

SERVER_URL = "http://127.0.0.1:8080"
SERVER_LOG = Path.home() / ".config" / "termuxai" / "llama-server.log"

CONTEXT_SIZE = 2048
STARTUP_TIMEOUT = 90


def server_is_running():
    try:
        response = httpx.get(
            f"{SERVER_URL}/health",
            timeout=2
        )
        return response.status_code == 200
    except httpx.RequestError:
        return False


def start_server():
    if server_is_running():
        return None

    llama_server = shutil.which("llama-server")

    if not llama_server:
        raise RuntimeError(
            "llama-server was not found. Install it with: pkg install llama-cpp"
        )

    if not MODEL_PATH.is_file():
        raise RuntimeError(
            f"Model file not found: {MODEL_PATH}"
        )

    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)

    command = [
        llama_server,
        "-m", str(MODEL_PATH),
        "-c", str(CONTEXT_SIZE),
        "--host", "127.0.0.1",
        "--port", "8080"
    ]

    with SERVER_LOG.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

    start_time = time.monotonic()

    while time.monotonic() - start_time < STARTUP_TIMEOUT:
        if process.poll() is not None:
            log = SERVER_LOG.read_text(
                encoding="utf-8",
                errors="replace"
            )

            raise RuntimeError(
                "llama-server stopped unexpectedly.\n\n"
                f"Server log:\n{log[-3000:]}"
            )

        if server_is_running():
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
        f"{STARTUP_TIMEOUT} seconds. Check {SERVER_LOG}"
    )


def stop_server(process):
    # Only stop a server started by this TermuxAI session.
    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
