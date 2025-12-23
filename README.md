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
*   **Global Hotkey**: Toggle listening from anywhere with `Win + Shift + V`.
    *   *The Windows key (⊞) is called "Super" in Linux settings.*
    *   *If the app is closed, this key will launch it.*
    *   *If the app is running, this key will toggle listening.*

---

## 📥 Installation Guide

Follow these steps to install the application, create a desktop shortcut, and pin it to your taskbar.

### Quick Install (Recommended)
Run the automated installer script. This handles **everything** including:
1.  Installing all system dependencies (`apt install ...`)
2.  Setting up the Python virtual environment
3.  Downloading the required speech model automatically
4.  Creating a desktop shortcut
5.  Registering the Global Hotkey (`Win + Shift + V`) in GNOME Settings

```bash
cd /home/bdavidriggins/Documents/VoxInput/
./install.sh
```

> **Note**: The installer will prompt for your password to install system packages via `sudo apt install`.

### Manual Dependency Installation (Optional)
If the installer fails or you prefer manual control, you can install dependencies first:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 libportaudio2 portaudio19-dev \
    xdotool ffmpeg unzip wget
```

*Note: `xdotool` is critical for typing text into other windows.*

### Pin to Taskbar (Ubuntu Dock)
Once installed, you can make VoxInput easy to access:
1.  Press the **Win** (⊞) key to open the Activities overview.
2.  Type **"VoxInput"**.
3.  You should see the VoxInput icon (Microphone).
4.  **Right-click** the icon.
5.  Select **"Add to Favorites"** (or "Pin to Dash").
6.  The icon is now permanently on your dock for one-click access!

---

## ⌨️ Keyboard Shortcut

| Shortcut | Action |
|----------|--------|
| **`Win + Shift + V`** | Toggle listening on/off (or launch app if closed) |

> **Windows Keyboard Users**: The `Win` key (⊞ Windows logo key) is called "Super" in Linux. They are the same key!

### After Installation
The keyboard shortcut is automatically registered during installation. If you need to verify or manually configure it:

1. Open **Settings** → **Keyboard** → **Keyboard Shortcuts** → **Custom Shortcuts**
2. Look for **"VoxInput Toggle"**
3. It should show the shortcut as `Super+Shift+V`

### First-Time Use After Install
Sometimes GNOME needs to refresh keybindings. If the shortcut doesn't work immediately:
- **Log out and log back in**, OR
- Run: `killall gsd-media-keys` (it will auto-restart)

---

## 🎙️ Usage

### Starting the App
*   Press **`Win + Shift + V`** to launch the app instantly.
*   OR Click the **VoxInput** icon on your taskbar.
*   Look for the **Microphone Icon** in your system tray (usually top-right corner of the screen).
    *   **Green Mic**: The app is open and ready.
    *   **Red Mic**: The app is actively listening and typing.

### Dictation
1.  Click into a text box (e.g., a document, Slack, or terminal).
2.  Press **`Win + Shift + V`** to start listening.
    *   *The icon will turn RED.*
3.  Speak clearly. Text will type out in real-time.
    *   *Note: Using the Vosk engine (default), text is lowercase and unpunctuated for speed.*
    *   *Note: Using the Whisper engine (in Settings), text is capitalized and punctuated but appears in sentence batches.*
4.  Press **`Win + Shift + V`** again to stop.

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

### File Structure
*   `src/main.py`: Entry point and main application logic.
*   `src/ui.py`: System Tray and Settings Window implementation (GTK).
*   `src/recognizer.py`: DeepSpeech/Vosk/Whisper engine wrappers.
*   `src/injection.py`: Handles keyboard simulation (xdotool/pynput).
*   `bin/toggle.sh`: Helper script for the global hotkey.
*   `install.sh`: Setup script (installs dependencies, model, and hotkey).

---

## 🔄 Uninstall or Reinstall

### Re-installing / Upgrading
If you have pulled new code or want to reset the environment:
1.  Simply run the installer script again. It is safe to re-run.
    ```bash
    ./install.sh
    ```
    This will check dependencies, update the virtual environment, and refresh the desktop shortcut.

### Uninstalling
To completely remove VoxInput from your system:

1.  **Remove the Desktop Shortcut**:
    ```bash
    rm ~/.local/share/applications/voxinput.desktop
    ```
2.  **Remove the Keyboard Shortcut**:
    ```bash
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[]"
    ```
3.  **Delete the Application Folder**:
    ```bash
    rm -rf /home/bdavidriggins/Documents/VoxInput
    ```
    *Note: This deletes the downloaded model files as well.*

---

## ❓ Troubleshooting

### Hotkey Doesn't Work
1.  Ensure you ran `./install.sh`.
2.  **Log out and log back in** (GNOME needs to refresh keybindings).
3.  Check: **Settings** → **Keyboard** → **Shortcuts** → **Custom Shortcuts**. You should see "VoxInput Toggle".
4.  If the shortcut shows but doesn't trigger, run:
    ```bash
    killall gsd-media-keys
    ```
5.  If that failed, manually add a shortcut:
    *   **Name**: VoxInput Toggle
    *   **Command**: `/home/bdavidriggins/Documents/VoxInput/bin/toggle.sh`
    *   **Shortcut**: Press `Win + Shift + V`

### Other Issues
*   **"Model not found"**: Ensure the `model/` directory exists and contains the Vosk model files.
*   **Typing is glitchy**: Ensure `xdotool` is installed (`sudo apt install xdotool`). It is much more reliable than the fallback method.
*   **Audio is silent**: Check your OS Sound Settings > Input. Make sure the correct microphone is selected and unmuted.

---

*Created with ❤️ for productivity*