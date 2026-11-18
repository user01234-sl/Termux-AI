# TermuxAI

A lightweight AI CLI client designed for Android phones running Termux.

Use online AI providers through API endpoints or run a local language model using llama.cpp.

## Features

- Interactive terminal menu
- Online AI support
- Offline AI support
- GGUF model manager with HTTPS downloads and per-model llama.cpp settings
- Conversation history
- Configurable settings
- Rich terminal interface
- ARM64 Android support

## Requirements

- Android phone with ARM64 architecture
- Termux
- Internet connection for installation and model downloads

## Installation

Update Termux:

```bash
pkg update && pkg upgrade
```

Install dependencies:

```bash
pkg install python git llama-cpp
```

Download TermuxAI:

```bash
git clone YOUR_REPOSITORY_URL
cd TermuxAI
```

Install:

```bash
chmod +x install.sh
./install.sh
```

## Launch

```bash
termuxai
```

## Online AI security

- Remote API endpoints must use HTTPS.
- Plain HTTP is accepted only for loopback addresses such as `localhost` and `127.0.0.1` (used by the local Offline AI server).
- API keys are stored separately from general settings, with owner-only file and directory permissions where the platform supports them.
- API redirects are not followed, and provider error bodies are not printed.
- The SQLite conversation-history directory and database use owner-only permissions where supported.
- Saved conversation history can be deleted from the Conversation History screen.
- Connection tests do not display arbitrary text returned by the provider.
- Provider object representations hide API keys to reduce accidental disclosure in debug output.
- Local llama.cpp logs use owner-only permissions where supported and raw log contents are not printed in error messages.
- Conversation-history save errors use generic messages instead of exposing raw exception details.

Keep your API key private. Do not share `~/.config/termuxai/secrets.json` or paste your key into screenshots, logs, or support messages. The key is stored as plaintext in a file protected by Android/Linux permissions; it is not encrypted by TermuxAI.

Conversation history is stored locally in `~/.local/share/termuxai/history.db`. Use the Conversation History screen's `D` option to delete all saved conversations. Deletion uses SQLite secure-delete and database compaction where supported, but cannot guarantee forensic erasure from flash storage or backups. Turn off `Save conversation history` in Configuration to prevent future chats from being saved.

## Offline AI

TermuxAI uses llama-cpp and a GGUF language model.

The model is downloaded separately and is not included in the Git repository.

By default, TermuxAI looks for the model at:

```text
~/.local/share/termuxai/models/
```

### Model Manager

Open **Model Manager** from the main menu to download direct HTTPS `.gguf` links,
select the active model, configure per-model context size, port, CPU threads and
GPU layers, view the generated `llama-server` command, or delete a managed model.
Models are stored in `~/.local/share/termuxai/models/` and the catalogue is stored
in `~/.local/share/termuxai/models.json` (or under `XDG_DATA_HOME`). Downloads
are streamed to a temporary file and renamed only after completion. TermuxAI
requires HTTPS, limits a model download to 20 GB, and binds llama.cpp to
`127.0.0.1` rather than exposing the local server to the network. The command
is assembled as an argument list and is never executed through a shell.

Use direct links to GGUF files. Some model hosting sites require accepting a
license or signing in first; those sites may not provide a usable direct link.
Check a model's source and license before downloading it. Ensure your phone has
enough free storage and memory for the model you choose.

## Uninstallation

From the project directory:

```bash
./uninstall.sh
```

Your personal settings, conversation history and downloaded models are preserved.

## Project Status

Version: 0.3.5

Currently under development.

## Platform

Designed specifically for Android phones running Termux (ARM64).

## License

To be decided.


### Importing existing models

Open **Model Manager → Import local GGUF model (copy)** and enter the full path to an existing `.gguf` file. TermuxAI copies it into its managed model directory and registers it in the model library. The original file is left untouched.
