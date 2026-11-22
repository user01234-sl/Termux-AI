from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from termuxai.providers.openai_compatible import (
    OpenAICompatibleProvider,
    APIError
)
from termuxai.providers.offline import (
    start_server,
    stop_server,
    get_active_model_config
)
from termuxai.security.secrets import get_api_key
from termuxai.core.history import (
    init_db,
    create_conversation,
    add_message,
    get_conversations,
    get_conversation,
    clear_history
)

console = Console()


def run_chat(provider, title, mode, settings):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant."
        }
    ]

    chat_id = None

    console.clear()

    console.print(
        Panel(
            f"[bold cyan]{title}[/]\n"
            "[dim]Type /exit to return to the main menu.[/]",
            border_style="cyan"
        )
    )

    while True:
        try:
            user_input = Prompt.ask(
                "\n[bold green]You[/]"
            ).strip()

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit"):
                break

            messages.append({
                "role": "user",
                "content": user_input
            })

            console.print("\n[bold cyan]AI[/]")

            response_parts = []

            try:
                console.print("[dim]Connecting...[/]")
                stream = provider.chat(messages)
                first_chunk = next(stream, None)

                if first_chunk is None:
                    console.print(
                        "[yellow]The API returned an empty response.[/]"
                    )
                    messages.pop()
                    continue

                response_parts.append(first_chunk)
                console.print(first_chunk, end="")

                for chunk in stream:
                    response_parts.append(chunk)
                    console.print(chunk, end="")

                console.print()

            except APIError as error:
                messages.pop()
                console.print(f"\n[red]API error: {error}[/]")
                continue

            assistant_reply = "".join(response_parts)

            messages.append({
                "role": "assistant",
                "content": assistant_reply
            })

            if settings["save_history"]:
                try:
                    if chat_id is None:
                        chat_id = create_conversation(mode)
                        console.print(
                            f"[dim]Chat ID: {chat_id}[/]"
                        )

                    add_message(chat_id, "user", user_input)
                    add_message(
                        chat_id,
                        "assistant",
                        assistant_reply
                    )

                except Exception:
                    # Do not echo raw exception details into the terminal; they
                    # may contain local paths or database/environment details.
                    console.print(
                        "\n[yellow]Could not save conversation history. "
                        "Check TermuxAI storage permissions.[/]"
                    )

        except KeyboardInterrupt:
            console.print(
                "\n[dim]Returning to main menu...[/]"
            )
            break


def online_chat(settings):
    api_key = get_api_key()

    if not api_key:
        console.print("[red]No API key configured.[/]")
        Prompt.ask("Press Enter to return", default="")
        return

    if not settings["api_base_url"] or not settings["api_model"]:
        console.print(
            "[red]API endpoint or model is not configured.[/]"
        )
        Prompt.ask("Press Enter to return", default="")
        return

    try:
        provider = OpenAICompatibleProvider(
            base_url=settings["api_base_url"],
            api_key=api_key,
            model=settings["api_model"]
        )
    except APIError as error:
        console.print(f"[red]Online AI configuration error: {error}[/]")
        Prompt.ask("Press Enter to return", default="")
        return

    run_chat(
        provider,
        "Online AI Chat",
        "online",
        settings
    )


def offline_chat(settings):
    process = None

    try:
        console.clear()

        model_config = get_active_model_config()

        console.print(
            Panel(
            "[bold cyan]Starting Offline AI...[/]\n"
            f"[dim]Loading {model_config['name']} on your device.[/]",
            border_style="cyan"
            )
        )

        console.print(f"[dim]Model: {model_config['name']}[/]")
        process = start_server(model_config)

        provider = OpenAICompatibleProvider(
            base_url=f"http://127.0.0.1:{model_config['port']}/v1",
            api_key="termuxai-local",
            model=model_config["name"]
        )

        run_chat(
            provider,
            "Offline AI Chat",
            "offline",
            settings
        )

    except (RuntimeError, OSError) as error:
        console.print(f"\n[red]Offline AI error: {error}[/]")
        Prompt.ask("Press Enter to return", default="")

    finally:
        if process is not None:
            console.print(
                "\n[dim]Stopping local AI server...[/]"
            )
            stop_server(process)


def conversation_history(settings):
    init_db()

    while True:
        console.clear()

        console.print(
            Panel(
                "[bold cyan]Conversation History[/]\n"
                "[dim]Saved conversations are read-only. You can also delete all saved history.[/]",
                border_style="cyan"
            )
        )

        conversations = get_conversations()

        if not conversations:
            console.print("[yellow]No saved conversations yet.[/]")
            Prompt.ask("Press Enter to return", default="")
            return

        table = Table(show_header=True)
        table.add_column("No.", style="cyan")
        table.add_column("Chat ID", style="green")
        table.add_column("Mode")
        table.add_column("Last Updated")

        for index, item in enumerate(conversations, 1):
            updated = item["updated_at"][:19].replace("T", " ")

            table.add_row(
                str(index),
                str(item["id"]),
                item["mode"].capitalize(),
                updated
            )

        console.print(table)
        console.print("\n[dim]Select a conversation to view its messages.[/]")
        console.print("[dim]Enter D to delete all saved conversations, or 0 to return.[/]")

        choices = [str(i) for i in range(len(conversations) + 1)] + ["d", "D"]

        choice = Prompt.ask(
            "\n[cyan]Select a conversation[/]",
            choices=choices,
            default="0"
        )

        if choice == "0":
            return

        if choice.lower() == "d":
            confirm = Prompt.ask(
                "Delete ALL saved conversations permanently? (y/n)",
                choices=["y", "n"],
                default="n"
            )
            if confirm == "y":
                try:
                    clear_history()
                    console.print("[green]Saved conversation history deleted.[/]")
                except Exception:
                    console.print("[red]Could not delete saved conversation history.[/]")
                Prompt.ask("Press Enter to continue", default="")
            continue

        selected = conversations[int(choice) - 1]

        conversation, messages = get_conversation(selected["id"])

        if conversation is None:
            console.print("[red]Conversation not found.[/]")
            Prompt.ask("Press Enter to continue", default="")
            continue

        console.clear()

        console.print(
            Panel(
                f"[bold cyan]Chat ID: {conversation['id']}[/]\n"
                f"[dim]Mode: {conversation['mode'].capitalize()}[/]",
                border_style="cyan"
            )
        )

        if not messages:
            console.print("[yellow]This conversation has no messages.[/]")

        for message in messages:
            role = message["role"]

            if role == "user":
                console.print("\n[bold green]You[/]")
            else:
                console.print("\n[bold cyan]AI[/]")

            console.print(message["content"])

            if settings["show_timestamps"]:
                console.print(
                    f"[dim]{message['timestamp'][:19].replace('T', ' ')}[/]"
                )

        Prompt.ask("\nPress Enter to return to history", default="")
