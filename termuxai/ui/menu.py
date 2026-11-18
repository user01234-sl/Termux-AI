from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()


def show_banner():
    console.clear()

    banner = """
 _____                                   _    ___
|_   _|__ _ __ _ __ ___  _   ___  __    / \  |_ _|
  | |/ _ \ '__| '_ ` _ \| | | \ \/ /   / _ \  | |
  | |  __/ |  | | | | | | |_| |>  <   / ___ \ | |
  |_|\___|_|  |_| |_| |_|\__,_/_/\_\ /_/   \_\___|
    """

    console.print(
        Panel(
            banner,
            title="[bold cyan]T E R M U X A I[/]",
            subtitle="[dim]Your AI. Your choice.[/]",
            border_style="cyan"
        )
    )


def main_menu():
    table = Table(show_header=False, box=None)

    options = [
        ("1", "Online AI", "Cloud-based AI"),
        ("2", "Offline AI", "Local language model"),
        ("3", "Model Manager", "Manage offline models"),
        ("4", "Provider Settings", "API configuration"),
        ("5", "Configuration", "Application preferences"),
        ("6", "Conversation History", "Browse saved conversations"),
        ("7", "Exit", "Close TermuxAI")
    ]

    for number, name, description in options:
        table.add_row(
            f"[bold cyan][{number}][/]",
            f"[bold]{name}[/]",
            f"[dim]{description}[/]"
        )

    console.print(table)


def configuration_menu(settings, save_callback):
    while True:
        console.clear()

        console.print(
            Panel(
                "[bold cyan]Configuration[/]",
                border_style="cyan"
            )
        )

        console.print(
            f"1. Save conversation history: {settings['save_history']}"
        )
        console.print(
            f"2. Show timestamps: {settings['show_timestamps']}"
        )
        console.print(
            f"3. Default mode: {settings['default_mode']}"
        )
        console.print("4. Back")

        choice = Prompt.ask(
            "\n[cyan]Select an option[/]",
            choices=["1", "2", "3", "4"],
            default="4"
        )

        if choice == "1":
            settings["save_history"] = not settings["save_history"]

        elif choice == "2":
            settings["show_timestamps"] = not settings["show_timestamps"]

        elif choice == "3":
            settings["default_mode"] = (
                "offline" if settings["default_mode"] == "online"
                else "online"
            )

        elif choice == "4":
            break

        save_callback(settings)

        console.print("\n[green]Settings saved.[/]")
        Prompt.ask("Press Enter to continue", default="")
