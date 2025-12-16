# VoxInput
**Native Linux Voice-to-Text Dictation System**

VoxInput is a powerful, privacy-first voice recognition tool for Linux (Ubuntu 24.04+). It runs entirely offline using the **Vosk** (real-time) and **Faster-Whisper** (high accuracy) engines, allowing you to dictate text into *any* application just like a keyboard.

## ✨ Key Features
*   **Real-time Typing**: Text appears instantly as you speak (using Vosk engine). No waiting for the sentence to finish.
*   **Universal Injection**: works in standard text editors, browsers, terminals, chat apps, etc.
*   **System Tray Integration**:
    *   **Green Icon**: Idle / Ready.
    *   **Red Icon**: Active / Listening.
    *   **Right-Click Menu**: Quick access to Engine switching and Settings.
*   **Global Hotkey**: Toggle listening from anywhere with `Super` + `M` (Windows Key + M).
*   **Privacy First**: All processing happens locally on your machine. No audio is sent to the cloud.

---

## 📥 Installation Guide

Follow these steps to install the application, create a desktop shortcut, and pin it to your taskbar.

### 1. Install System Dependencies
Open your terminal and run the following command to install required system libraries (GTK support, Audio, Text Control):

```bash
sudo apt update
sudo apt install python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 libportaudio2 portaudio19-dev xdotool ffmpeg
```
*Note: `xdotool` is critical for typing text into other windows.*

### 2. Run the Installer
Run the automated installer script. This will:
1.  Install necessary system dependencies.
2.  Set up the Python virtual environment.
3.  **Download the required speech model** automatically.
4.  Create a desktop shortcut.

Run this command in the project directory:
```bash
./install.sh
```
*If the installation succeeds, you will see a success message.*

### 3. Pin to Taskbar (Ubuntu Dock)
Once installed, you can make VoxInput easy to access:
1.  Press the **Super** (Windows) key to open the Activities overview.
2.  Type **"VoxInput"**.
3.  You should see the VoxInput icon (Microphone).
4.  **Right-click** the icon.
5.  Select **"Add to Favorites"** (or "Pin to Dash").
6.  The icon is now permanently on your dock for one-click access!

---

## 🎙️ Usage

### Starting the App
*   Click the **VoxInput** icon on your taskbar.
*   Look for the **Microphone Icon** in your system tray (usually top-right corner of the screen).
    *   **Green Mic**: The app is open and ready.
    *   **Red Mic**: The app is actively listening and typing.

### Dictation
1.  Click into a text box (e.g., a document, Slack, or terminal).
2.  Press **`Super` + `M`** OR **Double-Click** the tray icon to start listening.
    *   *The icon will turn RED.*
3.  Speak clearly. Text will type out in real-time.
    *   *Note: Using the Vosk engine (default), text is lowercase and unpunctuated for speed.*
    *   *Note: Using the Whisper engine (in Settings), text is capitalized and punctuated but appears in sentence batches.*
4.  Press **`Super` + `M`** again to stop.

### Context Menu (Right-Click Tray)
*   **Start/Stop Listening**: Manual toggle.
*   **Open Settings**:
    *   **Microphone**: Select specific input device.
    *   **Engine**: Switch between **Vosk** (Fast, Real-time) and **Whisper** (High Accuracy, Slower).
*   **Quit**: Completely close the application.

---

## 🛠️ Development

If you want to modify the code or run it manually:

### Manual Run
```bash
# Activate virtual environment
source venv/bin/activate

# Run the app
python3 run.py
```

### Running Tests
To verify audio devices and logic without running the full UI:
```bash
./venv/bin/python -m unittest discover tests
```

### File Structure
*   `src/main.py`: Entry point and main application logic.
*   `src/ui.py`: System Tray and Settings Window implementation (GTK).
*   `src/recognizer.py`: DeepSpeech/Vosk/Whisper engine wrappers.
*   `src/injection.py`: Handles keyboard simulation (xdotool/pynput).
*   `install.sh`: Setup script.

---

## ❓ Troubleshooting

*   **"Model not found"**: Ensure the `model/` directory exists and contains the Vosk model files.
*   **Typing is glitchy**: Ensure `xdotool` is installed (`sudo apt install xdotool`). It is much more reliable than the fallback method.
*   **Hotkey doesn't work**: On some Wayland composites, global hotkeys are restricted. You can bind a custom system shortcut to run:  
    `pkill -USR1 -f 'run.py'`  
    This signal toggles the listening state externally.
*   **Audio is silent**: Check your OS Sound Settings > Input. Make sure the correct microphone is selected and unmuted.

---
*Created by Antigravity*