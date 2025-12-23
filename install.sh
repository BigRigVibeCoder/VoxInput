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

# 5. Setup Global Hotkey (GNOME)
echo "Setting up Global Hotkey (Super+Shift+V)..."
TOGGLE_SCRIPT="$(pwd)/bin/toggle.sh"
chmod +x "$TOGGLE_SCRIPT"

# Use Python to safely append to gsettings list
export TOGGLE_SCRIPT_PATH="$TOGGLE_SCRIPT"
python3 << 'PYEOF'
import subprocess
import ast
import os

toggle_script = os.environ.get('TOGGLE_SCRIPT_PATH', '/home/bdavidriggins/Documents/VoxInput/bin/toggle.sh')

try:
    # 1. Get current custom keybindings list
    output = subprocess.check_output(['gsettings', 'get', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings']).decode('utf-8').strip()
    if output == '@as []' or output == '':
        current_list = []
    else:
        # gsettings returns variants like '@as []' sometimes, usually just "['path', ...]"
        # we strictly need to parse it. 
        if output.startswith('@as'):
            output = output[3:].strip()
        current_list = ast.literal_eval(output)

    # 2. Define our new binding path
    new_binding = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-voxinput/'
    
    # 3. Add if not present
    if new_binding not in current_list:
        current_list.append(new_binding)
        # Convert back to GVariant string format
        new_list_str = str(current_list)
        subprocess.run(['gsettings', 'set', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings', new_list_str], check=True)
        print('Added custom keybinding path to list.')
    else:
        print('Keybinding path already exists.')

    # 4. Set the properties for this binding
    base_cmd = ['gsettings', 'set', f'org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{new_binding}']
    subprocess.run(base_cmd + ['name', 'VoxInput Toggle'], check=True)
    subprocess.run(base_cmd + ['command', toggle_script], check=True)
    subprocess.run(base_cmd + ['binding', '<Super><Shift>v'], check=True)
    print('Successfully configured Super+Shift+V shortcut.')

except Exception as e:
    print(f'Failed to set hotkey: {e}')
    print(f'You may need to manually set the shortcut to: {toggle_script}')
PYEOF

# 6. Refresh GNOME keybindings (so hotkey works immediately without logout)
echo "Refreshing GNOME keybindings..."
killall gsd-media-keys 2>/dev/null || true
sleep 1

echo ""
echo "✅ Installation Complete!"
echo "You can now find VoxInput in your applications menu."
echo "Press Win+Shift+V to toggle voice dictation."
