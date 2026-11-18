from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from importlib.metadata import version, PackageNotFoundError

from termuxai.core.config import load_config, save_config
from termuxai.ui.menu import (
    show_banner,
    main_menu,
    configuration_menu
)
from termuxai.ui.provider_settings import provider_settings
from termuxai.ui.model_manager import model_manager
from termuxai.ui.chat import (
    online_chat,
    offline_chat,
    conversation_history
)

console = Console()


def show_coming_soon(feature):
    console.print(
        Panel(
            f"[yellow]{feature} is not implemented yet.[/]\n\n"
            "[dim]This feature will be added in a future development stage.[/]",
            title="[bold cyan]Under Development[/]",
            border_style="yellow"
        )
    )
    Prompt.ask("\nPress Enter to return", default="")


def run():
    settings = load_config()
    try:
        __version__ = version("termuxai")
    except PackageNotFoundError:
        __version__ = "unknown"

    while True:
        show_banner()

        console.print(
            f"[dim]Version {__version__} | Mode: {settings['default_mode']}[/]\n"
        )

        main_menu()

        choice = Prompt.ask(
            "\n[bold cyan]Select an option[/]",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="1"
        )

        if choice == "1":
            online_chat(settings)

        elif choice == "2":
            offline_chat(settings)

        elif choice == "3":
            model_manager()

        elif choice == "4":
            provider_settings(settings, save_config)

        elif choice == "5":
            configuration_menu(settings, save_config)

        elif choice == "6":
            conversation_history(settings)

        elif choice == "7":
            console.print(
                "\n[bold cyan]Thank you for using TermuxAI![/]"
            )
            break
