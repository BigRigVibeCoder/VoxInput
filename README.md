<div align="center">

# 🎙️ VoxInput

**Offline Voice-to-Text Dictation for Linux**

[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04+-E95420?logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*Dictate text into any application using your voice. 100% offline. 100% private.*

[**Quick Start**](#-quick-start) • [**Features**](#-features) • [**Troubleshooting**](#-troubleshooting) • [**Contributing**](#-contributing)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **Privacy-First** | All processing happens locally. No internet required. No data leaves your machine. |
| ⚡ **Real-Time** | Text appears instantly as you speak (Vosk engine) |
| 🎯 **Universal** | Works in any text field - browsers, terminals, editors, chat apps |
| ⌨️ **Global Hotkey** | Toggle with `Win+Shift+V` from anywhere |
| 🔄 **Dual Engines** | Vosk (fast, real-time) or Whisper (accurate, punctuated) |

---

## 🚀 Quick Start

### One-Line Install

```bash
git clone https://github.com/bdavidriggins/VoxInput.git && cd VoxInput && ./install.sh
```

The installer handles everything:
- ✅ System dependencies (`apt install ...`)
- ✅ Python virtual environment
- ✅ Speech recognition model download
- ✅ Desktop shortcut creation
- ✅ Global hotkey registration (`Win+Shift+V`)

### Usage

| Action | How |
|--------|-----|
| **Start app** | Press `Win+Shift+V` or click VoxInput in app menu |
| **Toggle dictation** | Press `Win+Shift+V` while app is running |
| **Stop dictation** | Press `Win+Shift+V` again |

**Tray Icon Colors:**
- 🟢 Green = Ready (not listening)
- 🔴 Red = Active (listening & typing)

---

## 📋 Requirements

- **OS**: Ubuntu 24.04+ (or compatible Linux with GNOME)
- **Python**: 3.10+
- **Audio**: Working microphone

---

## ⌨️ Keyboard Shortcut

> **Windows keyboard users**: The `Win` key (⊞) is called "Super" in Linux. Same key!

| Shortcut | Action |
|----------|--------|
| `Win + Shift + V` | Launch app OR toggle dictation |

---

## 🎙️ Speech Engines

Switch engines via the tray menu → Settings:

| Engine | Speed | Accuracy | Output Style |
|--------|-------|----------|--------------|
| **Vosk** (default) | ⚡ Real-time | Good | lowercase, no punctuation |
| **Whisper** | 🐢 Batched | Excellent | Capitalized, punctuated |

---
89: 
90: ## 🧠 Using Better VOSK Models
91: 
92: By default, the installer downloads a lightweight VOSK model (~40MB). It is fast but may make mistakes. For desktop dictation, the larger models (~2GB) are much more accurate.
93: 
94: **How to upgrade:**
95: 
96: 1. **Download the large English model**:
97:    - Go to: [https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models)
98:    - Download `vosk-model-en-us-0.22` (approx 1.8 GB).
99: 
100: 2. **Extract the file**:
101:    - Unzip the downloaded file. You will get a folder named `vosk-model-en-us-0.22`.
102: 
103: 3. **Move to VoxInput**:
104:    - Inside `VoxInput/model`, create a new folder (e.g. `large_model`).
105:    - Move the **contents** of the extracted folder into `VoxInput/model/large_model`.
106: 
107: 4. **Select in Settings**:
108:    - Open VoxInput **Settings**.
109:    - Select **Engine Type: Vosk**.
110:    - Click the folder icon next to **Vosk Model Path**.
111:    - Select your new `VoxInput/model/large_model` folder.
112:    - Click **Save**.
113: 
114: ---

## ⚡ How to Enable Whisper & GPU

Whisper can be significantly faster on a GPU. This app attempts to use your GPU automatically if available.

### 1. Enable Whisper
1. Click the VoxInput tray icon.
2. Go to **Settings** -> **Engine** -> **Whisper**.

### 2. Verify GPU Usage
When you start the application, check `voxinput.log`. You should see:
`INFO - Whisper model loaded successfully on device: cuda:0`

If you see a warning about "falling back to CPU", your GPU was not detected.

### ⚠️ GPU Compatibility Disclaimer
**This application is not "smart enough" to automatically install the correct GPU drivers for every single graphics card.**
It installs a standard version of PyTorch by default. If you have an older or specialized GPU (e.g., Maxwell, Pascal), you may need to manually install a compatible version of PyTorch.

**Example Fix for Older GPUs:**
If you have an older card (like Quadro M2200), you might need PyTorch with CUDA 11.8 support:
```bash
source venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Check [pytorch.org](https://pytorch.org/get-started/locally/) for the correct command for your specific hardware.

---

## 🔧 Troubleshooting

### Hotkey Not Working?

1. **Verify daemon is running:**
   ```bash
   pgrep gsd-media-keys || /usr/libexec/gsd-media-keys &
   ```

2. **Check shortcut exists:**
   - Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts
   - Look for "VoxInput Toggle"

3. **Re-run installer:**
   ```bash
   ./install.sh
   ```

4. **Log out and log back in** (refreshes GNOME keybindings)

### Other Issues

| Problem | Solution |
|---------|----------|
| "Model not found" | Re-run `./install.sh` to download model |
| Typing is glitchy | Install xdotool: `sudo apt install xdotool` |
| No audio input | Check Settings → Sound → Input device |

---

## 📁 Project Structure

```
VoxInput/
├── install.sh          # One-click installer
├── run.py              # Entry point
├── src/
│   ├── main.py         # Application logic
│   ├── ui.py           # System tray UI (GTK)
│   ├── recognizer.py   # Vosk/Whisper engines
│   ├── injection.py    # Keyboard simulation
│   └── config.py       # Configuration
├── bin/
│   └── toggle.sh       # Hotkey handler script
├── assets/             # Tray icons
└── model/              # Speech model (auto-downloaded)
```

---

## 🛠️ Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run manually
python3 run.py

# View logs
tail -f voxinput.log
```

---

---
183: 
184: ## 📦 Deployment on Other Machines
185: 
186: To install VoxInput on another computer, you can create a standalone zip package:
187: 
188: ### 1. Create a Release Package
189: Run this script on your development machine:
190: ```bash
191: ./bin/create_package.sh
192: ```
193: This will generate a file named `VoxInput_v1.0.zip`.
194: 
195: ### 2. Install on New Machine
196: 1. Copy `VoxInput_v1.0.zip` to the new computer.
197: 2. Unzip it.
198: 3. Run the installer:
199:    ```bash
200:    cd VoxInput_v1.0
201:    ./install.sh
202:    ```
203: 
204: **Note**: The installer will automatically download the standard model if it's not included in the zip (which keeps the zip file small).
205: 
206: ---
207: 
208: ## 🔄 Reinstall / Update

To fix issues or update to the latest version:

### Option 1: Quick Update
Run the installer again. It is safe to run multiple times:
```bash
./install.sh
```

### Option 2: Clean Reinstall
If you are facing deep issues (like corrupted Python environments), perform a clean install:

1. **Delete the virtual environment**:
   ```bash
   rm -rf venv
   ```
2. **Run the installer**:
   ```bash
   ./install.sh
   ```

---

## 🗑️ Uninstall

```bash
# 1. Remove desktop shortcut
rm ~/.local/share/applications/voxinput.desktop

# 2. Remove keyboard shortcut
# Go to Settings -> Keyboard -> Shortcuts -> Custom Shortcuts
# Find "VoxInput Toggle" and remove it.
# (Or use CLI if you know the specific path, but manual is safer to avoid wiping other shortcuts)

# 3. Delete project folder
rm -rf /path/to/VoxInput
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for the Linux community**

⭐ Star this repo if it helped you!

</div>