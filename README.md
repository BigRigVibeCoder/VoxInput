# VoxInput

Native Linux Voice-to-Text System for Ubuntu 24.04.

## Features
- Global voice input (Super+M to toggle)
- Offline speech recognition using Vosk
- System tray integration
- Input injection into any application
- If the tray icon doesn't appear, ensure you have AppIndicator support enabled in your desktop environment (GNOME Shell Extension might be needed on standard Ubuntu if not pre-installed).
- If "Model not found" error occurs, check `src/config.py` paths.

### Logs
Logs are written to `voxinput.log` in the project root directory. Check this file for detailed error messages if the application fails to start or behaves unexpectedly.

## Installation

### Prerequisites
```bash
sudo apt install python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 libportaudio2
```

### Quick Setup (Recommended)
Run the automated installer:
```bash
./install.sh
```
This will create the virtual environment, install python dependencies, and add "VoxInput" to your system Applications menu.

### Manual Setup
1. Create virtual environment (system site packages required for GTK):
   ```bash
   python3 -m venv venv --system-site-packages
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure the Vosk model is in `model/`.

## Usage
**Option 1: Desktop Shortcut**
Search for "VoxInput" in your Applications menu and launch it.

**Option 2: Terminal**
```bash
./venv/bin/python -m src.main
```

### Controls & Usage
- **Global Hotkey:** `Ctrl` + `Alt` + `M` (Toggle Listening)
- **Tray Icon:**
  - **Left Click (Double Click):** Start/Stop Listening.
  - **Right Click:** Open Menu (Settings, Start/Stop with shortcut reminder, Quit).
  - **Indicators:**
    - **Green:** Ready (Idle).
    - **Red:** Listening (Recording).
    - **Flashing:** Processing state change.
- **Settings:** Right-click -> "Open Settings" to configure Microphone and Engine (Vosk/Whisper).
  (Useful for binding custom Wayland system shortcuts).

### Troubleshooting
- If "Model not found" error occurs, check `src/config.py` paths.
- If audio is silent, right-click the tray icon -> Settings -> Microphone and select "System Default (Follows OS Settings)".

## Development

### Running Tests
Run the unit test suite to verify audio inputs, model loading, and environment configuration:
```bash
./venv/bin/python -m unittest discover tests
```

### Manual Start/Stop
- **Start (Debug Mode):**
  ```bash
  ./venv/bin/python -m src.main
  ```
- **Stop (Force Kill):**
  ```bash
  pkill -f "python -m src.main"
  ```
