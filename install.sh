#!/data/data/com.termux/files/usr/bin/bash

set -e

echo "================================"
echo "       TermuxAI Installer"
echo "================================"

# Check Termux
if [ -z "$PREFIX" ] || [ ! -d "$PREFIX" ]; then
    echo "Error: This installer requires Termux."
    exit 1
fi

# Check architecture
if [ "$(uname -m)" != "aarch64" ]; then
    echo "Error: TermuxAI currently supports ARM64 only."
    exit 1
fi

# Check required files
if [ ! -f "setup.py" ] || [ ! -f "requirements.txt" ]; then
    echo "Error: Run this script from the TermuxAI project directory."
    exit 1
fi

echo
echo "Checking dependencies..."

# Install Python if needed
if ! command -v python >/dev/null 2>&1; then
    pkg install python -y
fi

# Check llama.cpp
if ! command -v llama-server >/dev/null 2>&1; then
    echo
    echo "Installing llama-cpp..."
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