#!/data/data/com.termux/files/usr/bin/bash

set -e

echo "================================"
echo "       TermuxAI Uninstaller"
echo "================================"

if [ -z "$PREFIX" ] || [ ! -d "$PREFIX" ]; then
    echo "Error: This script requires Termux."
    exit 1
fi

echo
echo "This will uninstall the TermuxAI Python package."
echo
echo "Your personal data will be preserved:"
echo "  - API settings"
echo "  - Conversation history"
echo "  - Downloaded AI models"
echo "  - Project source files"
echo

read -r -p "Continue? [y/N]: " answer

case "$answer" in
    y|Y|yes|YES)
        python -m pip uninstall termuxai -y
        echo
        echo "TermuxAI has been uninstalled."
        echo "Your personal data and project files were preserved."
        ;;
    *)
        echo "Uninstallation cancelled."
        ;;
esac