#!/bin/bash

# VoxInput Installer
# This script sets up the local environment and creates a desktop shortcut.

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "============================================="
echo "   VoxInput Installation Script"
echo "============================================="

# 0. Check System Dependencies
echo "[+] Checking system dependencies..."
MISSING_DEPS=0

if ! command -v xdotool &> /dev/null; then
    echo "ERROR: 'xdotool' is not installed. It is required for text injection."
    echo "       Install it with: sudo apt install xdotool"
    MISSING_DEPS=1
fi

if ! dpkg -s libportaudio2 &> /dev/null && ! dpkg -s portaudio19-dev &> /dev/null; then
    echo "WARNING: PortAudio libraries not found. Audio capture might fail."
    echo "         Recommended: sudo apt install libportaudio2 portaudio19-dev"
    # We don't fail, just warn, as manual compile might exist.
fi

if [ $MISSING_DEPS -ne 0 ]; then
    echo "Please install missing dependencies and run this script again."
    exit 1
fi

# 1. Setup Virtual Environment
echo "[+] Setting up Python environment..."
if [ ! -d "venv" ]; then
    # We use --system-site-packages to leverage apt-installed GI/GTK libs
    python3 -m venv venv --system-site-packages
    echo "    Created 'venv'."
else
    echo "    'venv' already exists."
fi

# 2. Install Dependencies
echo "[+] Installing Python requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Process Desktop File
echo "[+] Configuring desktop integration..."
TARGET_OP="$HOME/.local/share/applications/voxinput.desktop"

# Replace %PWD% with actual path in desktop file and save to target
sed "s|%PWD%|$DIR|g" voxinput.desktop > "$TARGET_OP"

# 4. Make it executable
chmod +x "$TARGET_OP"
echo "    Created: $TARGET_OP"

echo ""
echo "============================================="
echo "   Installation Successful!"
echo "============================================="
echo "1. You can now find 'VoxInput' in your Applications Menu."
echo "   (Press Super/Windows key and type 'VoxInput')"
echo "2. Right-click the app icon in the menu to 'Add to Favorites' (Pin to Dash)."
echo "3. Usage:"
echo "   - Status Icon will appear in Top Right (System Tray)."
echo "   - Green = Idle. Red = Listening."
echo "   - Toggle Key: Ctrl+Alt+M"
echo "============================================="
