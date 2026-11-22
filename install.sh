#!/data/data/com.termux/files/usr/bin/bash

set -e

INSTALL_OFFLINE=0

usage() {
    cat <<'USAGE'
TermuxAI installer

Usage:
  ./install.sh                 Install TermuxAI (online AI)
  ./install.sh --with-offline  Also install llama.cpp for offline AI
  ./install.sh --help          Show this help

Offline AI can also be added later with: pkg install llama-cpp
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --with-offline)
            INSTALL_OFFLINE=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

echo "================================"
echo "       TermuxAI Installer"
echo "================================"

# Check Termux
if [ -z "${PREFIX:-}" ] || [ ! -d "$PREFIX" ] || [ ! -x "$PREFIX/bin/pkg" ]; then
    echo "Error: This installer requires Termux."
    exit 1
fi

# Check architecture
if [ "$(uname -m)" != "aarch64" ]; then
    echo "Error: TermuxAI currently supports ARM64 (aarch64) only."
    exit 1
fi

# Check required files
if [ ! -f "setup.py" ] || [ ! -f "requirements.txt" ]; then
    echo "Error: Run this script from the TermuxAI project directory."
    exit 1
fi

echo
echo "Checking dependencies..."

if ! command -v python >/dev/null 2>&1; then
    echo "Installing Python..."
    pkg install python -y
fi

if [ "$INSTALL_OFFLINE" -eq 1 ] && ! command -v llama-server >/dev/null 2>&1; then
    echo
    echo "Installing optional offline AI support..."
    pkg install llama-cpp -y
fi

echo
echo "Installing TermuxAI..."
python -m pip install .

echo
echo "================================"
echo "     Installation complete!"
echo "================================"
echo
echo "Start TermuxAI using:"
echo "  termuxai"

if [ "$INSTALL_OFFLINE" -eq 0 ] && ! command -v llama-server >/dev/null 2>&1; then
    echo
    echo "Offline AI is not installed (this is optional)."
echo "To add it later, run: pkg install llama-cpp"
fi
