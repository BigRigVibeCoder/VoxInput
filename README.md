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

## 🗑️ Uninstall

```bash
# Remove desktop shortcut
rm ~/.local/share/applications/voxinput.desktop

# Remove keyboard shortcut
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[]"

# Delete project folder
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