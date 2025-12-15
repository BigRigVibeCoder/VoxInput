#!/bin/bash

# VoxInput Installer
# This script sets up the environment and installs the application shortcut.

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Installing VoxInput in: $DIR"

# 1. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv --system-site-packages
else
    echo "Virtual environment exists."
fi

# 2. Install Dependencies
echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# 3. Process Desktop File
echo "Configuring desktop shortcut..."
# Replace %PWD% with actual path in desktop file
sed "s|%PWD%|$DIR|g" voxinput.desktop > ~/.local/share/applications/voxinput.desktop

# 4. Make it executable
chmod +x ~/.local/share/applications/voxinput.desktop

echo ""
echo "============================================="
echo "Installation Complete!"
echo "============================================="
echo "1. Run the app from your Applications menu (search 'VoxInput')."
echo "2. Default Hostkey: Ctrl+Alt+M"
echo "3. Tray Icon: Use the 'Settings' menu to pick your microphone."
echo ""
echo "Troubleshooting Hotkeys:"
echo "If the hotkey doesn't work (common on Wayland), you can bind a system shortcut to:"
echo "Command: pkill -USR1 -f 'python -m src.main'"
echo "This command will toggle listening on/off."
echo "============================================="
