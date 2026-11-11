# TermuxAI

A lightweight AI CLI client designed for Android phones running Termux.

Use online AI providers through API endpoints or run a local language model using llama.cpp.

## Features

- Interactive terminal menu
- Online AI support
- Offline AI support
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

## Offline AI

TermuxAI uses llama.cpp and a GGUF language model.

The model is downloaded separately and is not included in the Git repository.

## Uninstallation

From the project directory:

```bash
./uninstall.sh
```

Your personal settings, conversation history and downloaded models are preserved.

## Project Status

Version: 0.3.0

Currently under development.

## Platform

Designed specifically for Android phones running Termux (ARM64).

## License

To be decided.
