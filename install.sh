#!/bin/bash
set -e

echo "Starting VoxInput Installation..."

# 1. Install System Dependencies
echo "Installing system dependencies..."
# Check if sudo is available or if we are root
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "This script requires root privileges to install packages. Please run as root or install sudo."
    exit 1
  fi
else
    SUDO=""
fi

$SUDO apt update
$SUDO apt install -y python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 libportaudio2 portaudio19-dev xdotool ffmpeg unzip wget

# 2. Setup Python Environment
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 3. Download Model if missing
MODEL_DIR="model"
if [ ! -d "$MODEL_DIR" ]; then
    echo "Downloading Vosk model..."
    # Using a reliable small model
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 "$MODEL_DIR"
    rm vosk-model-small-en-us-0.15.zip
    echo "Model installed."
else
    echo "Model directory exists, skipping download."
fi

# 4. Create Desktop Shortcut
echo "Creating Desktop Entry..."
cat > voxinput.desktop << EOL
[Desktop Entry]
Name=VoxInput
Comment=Voice-to-Text Dictation
Exec=$(pwd)/venv/bin/python $(pwd)/run.py
Icon=$(pwd)/assets/icon_idle.svg
Terminal=false
Type=Application
Categories=Utility;Accessibility;
Keywords=Voice;Dictation;Speech;
EOL

# Install to user applications
mkdir -p ~/.local/share/applications
cp voxinput.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/voxinput.desktop

echo "Installation Complete!"
echo "You can now find VoxInput in your applications menu."
echo "If the icon does not appear immediately, you may need to log out and log back in."
