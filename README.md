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
sudo apt install python3-pip python3-venv python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-appindicator3-0.1 libportaudio2
```

### Setup
1. Clone the repository
2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Download Vosk model:
   - Download a small model from [vosk-models](https://alphacephei.com/vosk/models) (e.g., `vosk-model-small-en-us-0.15`).
   - Extract it to `model/` directory in the project root.

## Usage
Run the application:
```bash
python3 run.py
```
- A microphone icon will appear in the system tray.
- Press **Super+M** or click "Start Listening" to begin dictation.
- Speak clearly.
- Press **Super+M** again or stop via tray to finish. Text will be typed at your cursor.
