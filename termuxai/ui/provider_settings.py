from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from termuxai.security.secrets import (
    prompt_for_api_key,
    get_api_key,
    delete_api_key
)
from termuxai.providers.openai_compatible import (
    OpenAICompatibleProvider,
    APIError,
    validate_base_url
)

console = Console()


def test_connection(settings):
    api_key = get_api_key()

    if not api_key:
        console.print("[red]API key is not configured.[/]")
        return

    if not settings["api_base_url"] or not settings["api_model"]:
        console.print("[red]Endpoint or model is not configured.[/]")
        return

    provider = OpenAICompatibleProvider(
        settings["api_base_url"],
        api_key,
        settings["api_model"]
    )

    try:
        console.print("[cyan]Testing connection...[/]")
        response = "".join(
            provider.chat([
                {
                    "role": "user",
                    "content": "Reply with OK."
                }
            ])
        )

        if response.strip():
            # Do not display arbitrary provider output during a connection test.
            # A malicious or misconfigured endpoint could echo sensitive data.
            console.print("[green]Connection successful; a response was received.[/]")
        else:
            console.print("[yellow]Connected, but received an empty response.[/]")

    except APIError as error:
        console.print(f"[red]Connection failed: {error}[/]")


def provider_settings(settings, save_callback):
    while True:
        console.clear()
        console.print(
            Panel(
                "[bold cyan]Online AI Provider Settings[/]",
                border_style="cyan"
            )
        )

        console.print(f"1. API endpoint: {settings['api_base_url'] or 'Not set'}")
        console.print(f"2. Model: {settings['api_model'] or 'Not set'}")
        console.print(f"3. API key: {'Configured' if get_api_key() else 'Not configured'}")
        console.print("4. Delete API key")
        console.print("5. Test connection")
        console.print("6. Back")

        choice = Prompt.ask(
            "\n[cyan]Select an option[/]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="6"
        )

        if choice == "1":
            value = Prompt.ask("API base URL").strip()

            try:
                settings["api_base_url"] = validate_base_url(value)
                save_callback(settings)
                console.print("[green]Endpoint saved.[/]")
            except APIError as error:
                console.print(f"[red]{error}[/]")

        elif choice == "2":
            value = Prompt.ask("Model name").strip()

            if value:
                settings["api_model"] = value
                save_callback(settings)
                console.print("[green]Model saved.[/]")
            else:
                console.print("[red]Model name cannot be empty.[/]")

        elif choice == "3":
            prompt_for_api_key()

        elif choice == "4":
            confirm = Prompt.ask(
                "Delete the saved API key? (y/n)",
                choices=["y", "n"],
                default="n"
            )
            if confirm == "y":
                delete_api_key()

        elif choice == "5":
            test_connection(settings)

        elif choice == "6":
            break

        Prompt.ask("\nPress Enter to continue", default="")
