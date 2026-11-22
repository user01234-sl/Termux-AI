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

Install the basic dependencies:

```bash
pkg install python git
```

`llama-cpp` is optional. Install it only if you want to run local GGUF models.

Download TermuxAI:

```bash
git clone https://github.com/user01234-sl/Termux-AI.git
cd Termux-AI
```

Install:

```bash
chmod +x install.sh
./install.sh
```

The default installation supports online AI and does not install the local
inference engine. To install offline AI support too, use:

```bash
./install.sh --with-offline
```

You can also add offline support later:

```bash
pkg install llama-cpp
```

## Launch

```bash
termuxai
```

> Menu preview 
<img width="1080" height="2400" alt="Termux-AI main menu" src="https://github.com/user-attachments/assets/6dce4845-0ee4-4458-8d74-7415690f2508" />

## Online AI security

- Remote API endpoints must use HTTPS.
- Plain HTTP is accepted only for loopback addresses such as `localhost` and `127.0.0.1` (used by the local Offline AI server).
- API keys are stored separately from general settings, with owner-only file and directory permissions where the platform supports them.
- API redirects are not followed, and provider error bodies are not printed.
- The SQLite conversation-history directory and database use owner-only permissions where supported.
- Saved conversation history can be deleted from the Conversation History screen.
- Connection tests do not display arbitrary text returned by the provider.
- Provider object representations hide API keys to reduce accidental disclosure in debug output.
- Secret, configuration, model-catalogue, local-server-log and history files reject symbolic links and use no-follow protections where the platform supports them.
- Private storage directories reject symbolic links; the SQLite database is created with owner-only permissions before SQLite opens it.
- Configuration values are type-checked and bounded when loaded.
- AI responses, saved messages and model names are displayed as untrusted terminal text; terminal control characters and bidirectional overrides are removed.
- Local llama.cpp logs use owner-only permissions where supported and raw log contents are not printed in error messages.
- Conversation-history save errors use generic messages instead of exposing raw exception details.

Keep your API key private. Do not share `~/.config/termuxai/secrets.json` or paste your key into screenshots, logs, or support messages. The key is stored as plaintext in a file protected by Android/Linux permissions; it is not encrypted by TermuxAI. These protections help against other Android apps and accidental disclosure, but they do not protect secrets from a compromised device, a malicious process running as the same Android app user, or someone with access to your unlocked Termux environment.

Conversation history is stored locally in `~/.local/share/termuxai/history.db`. Use the Conversation History screen's `D` option to delete all saved conversations. Deletion uses SQLite secure-delete and database compaction where supported, but cannot guarantee forensic erasure from flash storage or backups. Turn off `Save conversation history` in Configuration to prevent future chats from being saved.

## Offline AI

> Offline chat
<img width="1080" height="2400" alt="Termux-AI offline chat" src="https://github.com/user-attachments/assets/d76bc25a-3de4-45de-bea9-0e18752ec5af" />

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

Version: 0.4.1

Currently under development.

## Platform

Designed specifically for Android phones running Termux (ARM64).

## License

Termux-AI is licensed under the
GNU General Public License v3.0.

See [LICENSE](LICENSE) for details.


### Importing existing models

Open **Model Manager → Import local GGUF model (copy)** and enter the full path to an existing `.gguf` file. TermuxAI copies it into its managed model directory and registers it in the model library. The original file is left untouched.
