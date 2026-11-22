"""Interactive model manager."""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from termuxai.models.manager import (
    MODEL_DIR, load_catalog, download_model, import_model, set_active_model,
    update_model_settings, delete_model,
)

from termuxai.ui.safe_output import safe_terminal_text

console = Console()


def _show_models(catalog):
    table = Table(title="Downloaded GGUF Models")
    table.add_column("Active", style="green")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    table.add_column("Context", justify="right")
    table.add_column("Port", justify="right")
    for item in catalog["models"]:
        path = MODEL_DIR / item["filename"]
        size = path.stat().st_size / (1024 ** 3) if path.exists() else 0
        table.add_row(
            "*" if item["id"] == catalog["active_model"] else "",
            Text(safe_terminal_text(item["name"])),
            f"{size:.2f} GB",
            str(item["context_size"]),
            str(item["port"]),
        )
    console.print(table)


def _download():
    console.print("[dim]Use a direct HTTPS link to a .gguf file. Large downloads may take time.[/]")
    url = Prompt.ask("Model URL").strip()
    filename = Prompt.ask("Save as (filename.gguf)").strip()
    console.print(
        "[dim]Optional: enter the SHA-256 published by the model's trusted source. "
        "Leave blank if no trusted checksum is available.[/]"
    )
    expected_sha256 = Prompt.ask("Expected SHA-256", default="").strip() or None
    task_state = {"task": None}
    with Progress("[progress.description]{task.description}", BarColumn(), DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(), console=console) as progress:
        def report(current, total):
            if task_state["task"] is None:
                task_state["task"] = progress.add_task("Downloading model", total=total)
            progress.update(task_state["task"], completed=current, total=total)
        try:
            item = download_model(
                url, filename, report, expected_sha256=expected_sha256
            )
        except ValueError as error:
            console.print(
                f"Download failed: {safe_terminal_text(error)}",
                markup=False,
                highlight=False,
            )
            return
        except Exception:
            console.print("Download failed. Check the HTTPS URL, connection, and available storage.")
            return
    console.print(
        f"Downloaded and registered: {safe_terminal_text(item['name'])}",
        markup=False, highlight=False,
    )


def _import():
    console.print("[dim]Copy an existing .gguf model into TermuxAI. The original file will remain unchanged.[/]")
    source = Prompt.ask("Path to .gguf model file").strip()
    try:
        item = import_model(source)
        console.print(
            f"Imported and registered: {safe_terminal_text(item['name'])}",
            markup=False, highlight=False,
        )
    except (OSError, ValueError, FileExistsError) as error:
        console.print(f"Import failed: {safe_terminal_text(error)}", markup=False, highlight=False)


def _configure(item):
    console.print(
        f"Settings for {safe_terminal_text(item['name'])}",
        markup=False, highlight=False,
    )
    console.print("Enter 0 for automatic thread count or no GPU offload.")
    context = IntPrompt.ask("Context size", default=item["context_size"])
    port = IntPrompt.ask("Server port", default=item["port"])
    threads = IntPrompt.ask("CPU threads (0 = llama.cpp default)", default=item["threads"])
    gpu_layers = IntPrompt.ask("GPU layers (0 = CPU only)", default=item["gpu_layers"])
    try:
        update_model_settings(item["id"], context_size=context, port=port, threads=threads, gpu_layers=gpu_layers)
        console.print("[green]Model settings saved.[/]")
    except ValueError as error:
        console.print(f"[red]{error}[/]")


def model_manager():
    while True:
        console.clear()
        console.print("[bold cyan]Model Manager[/]")
        console.print(f"[dim]Model directory: {MODEL_DIR}[/]\n")
        try:
            catalog = load_catalog()
        except RuntimeError as error:
            console.print(f"[red]{error}[/]")
            Prompt.ask("Press Enter to return", default="")
            return
        if catalog["models"]:
            _show_models(catalog)
        else:
            console.print("[yellow]No models in the library yet.[/]")
        console.print("\n1. Download model from HTTPS URL")
        console.print("2. Import local GGUF model (copy)")
        console.print("3. Select active model")
        console.print("4. Configure model startup settings")
        console.print("5. Show llama.cpp startup command")
        console.print("6. Delete a model")
        console.print("7. Back")
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
        if choice == "1":
            _download()
        elif choice == "2":
            _import()
        elif choice in ("3", "4", "5", "6"):
            catalog = load_catalog()
            if not catalog["models"]:
                console.print("[yellow]Import or download a model first.[/]")
            else:
                for index, item in enumerate(catalog["models"], 1):
                    console.print(
                        f"{index}. {safe_terminal_text(item['name'])}",
                        markup=False, highlight=False,
                    )
                index = IntPrompt.ask("Model number", default=1)
                if not 1 <= index <= len(catalog["models"]):
                    console.print("[red]Invalid model number.[/]")
                else:
                    item = catalog["models"][index - 1]
                    if choice == "3":
                        set_active_model(item["id"])
                        console.print(
                            f"{safe_terminal_text(item['name'])} is now active.",
                            markup=False, highlight=False,
                        )
                    elif choice == "4":
                        _configure(item)
                    elif choice == "5":
                        command = ["llama-server", "-m", str(MODEL_DIR / item["filename"]), "-c", str(item["context_size"]), "--host", "127.0.0.1", "--port", str(item["port"])]
                        if item["threads"]:
                            command += ["--threads", str(item["threads"])]
                        if item["gpu_layers"]:
                            command += ["--n-gpu-layers", str(item["gpu_layers"])]
                        console.print("[bold]Startup command (arguments are safely passed without a shell):[/]")
                        console.print(" ".join(repr(part) for part in command))
                    elif choice == "6":
                        if Confirm.ask(
                            "Delete the selected model and its model file?",
                            default=False,
                        ):
                            try:
                                delete_model(item["id"])
                                console.print("[green]Model deleted.[/]")
                            except (OSError, ValueError) as error:
                                console.print(f"[red]Could not delete model: {error}[/]")
        if choice == "7":
            return
        Prompt.ask("\nPress Enter to continue", default="")
