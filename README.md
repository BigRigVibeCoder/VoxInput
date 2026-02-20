<div align="center">

<img src="assets/icon_active.svg" width="96" alt="VoxInput Logo"/>

# VoxInput

**Privacy-first, offline voice dictation for Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://ubuntu.com)
[![Engine](https://img.shields.io/badge/Engine-Vosk%20%7C%20Whisper-purple.svg)](https://alphacephei.com/vosk/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*Dictate text into any application, any text field, anywhere on your desktop.*  
*Zero cloud. Zero subscriptions. Zero data leaving your machine.*

[**Quick Start**](#-quick-start) · [**Architecture**](#-architecture) · [**Performance**](#-performance) · [**Configuration**](#️-configuration) · [**Contributing**](#-contributing)

</div>

---

## Why VoxInput?

Every major voice dictation solution sends your audio to a remote server. VoxInput runs **entirely offline** — your words never leave your machine. It integrates at the OS level via the system tray, works in every application, and is fast enough for real-time coding and writing.

```
You speak → Vosk/Whisper transcribes locally → ydotool injects text → done
```

No accounts. No API keys. No cloud dependency. Just your voice and your hardware.

---

## ✨ Features

| Feature | Detail |
|---------|--------|
| 🔒 **100% Offline** | All ML inference runs locally — Vosk KALDI or faster-whisper |
| ⚡ **Real-Time Streaming** | Text appears word-by-word as you speak (Vosk engine) |
| 🎯 **Universal Injection** | Works in any app — browser, terminal, VS Code, chat, Electron apps |
| 🖥️ **System Tray** | Lives as a tray icon. Right-click → Settings. Left-click → toggle. |
| 🧠 **OSD Overlay** | Floating on-screen display shows live recognition + mic level bar |
| ✏️ **Spell Correction** | SymSpellPy post-processing fixes ASR artifacts and common errors |
| 🔊 **Mic Enhancement** | Input volume, ALSA boost, WebRTC noise suppression (PulseAudio) |
| 🔧 **Tabbed Settings** | Dark-themed settings window — Audio, Engine, Processing tabs |
| 🚀 **Fast Startup** | Model loads in background thread — tray icon appears in ~0.5s |
| ⚙️ **C Extension RMS** | Custom `rms.c` via ctypes — 2× faster than NumPy for audio energy |
| 🔄 **Dual Engine** | Toggle between Vosk (real-time) and Whisper (accurate) at runtime |
| 📊 **Enterprise Logging** | SQLite black-box log at TRACE level for full forensic replay |

---

## 🚀 Quick Start

### One-Line Install

```bash
git clone https://github.com/bdavidriggins/VoxInput.git && cd VoxInput && ./install.sh
```

The installer handles everything — no manual steps required:

```
✅ System dependencies (apt)
✅ Python 3.10+ virtual environment
✅ Vosk gigaspeech model download (~1.4GB)
✅ faster-whisper + SymSpellPy pip packages
✅ C RMS extension (gcc -O3 build)
✅ Desktop icon (GNOME tray + ~/Desktop)
✅ GNOME custom keyboard shortcut (Super+Shift+V)
```

### Usage

| Action | How |
|--------|-----|
| **Launch** | Desktop icon or app menu search "VoxInput" |
| **Toggle dictation** | Left-click tray icon — or — `Super+Shift+V` |
| **Open settings** | Right-click tray icon → Settings |
| **Quit** | Right-click tray icon → Quit |

**Tray icon states:**
- `icon_idle.svg` — loaded, not listening
- `icon_active.svg` — actively capturing and transcribing

---

## 🏗️ Architecture

VoxInput is built around three concurrent threads that avoid blocking each other:

```
┌─────────────────────────────────────────────────────────────┐
│                        GTK Main Thread                       │
│   SystemTrayApp · SettingsDialog · OSDOverlay               │
└──────────────────────────┬──────────────────────────────────┘
                           │ GLib.idle_add (thread-safe UI updates)
          ┌────────────────┴────────────────┐
          │                                 │
┌─────────▼──────────┐           ┌──────────▼──────────┐
│  _process_loop      │           │  _injection_thread   │
│  (audio thread)     │           │  (xdotool/ydotool)  │
│                     │           │                      │
│  AudioCapture       │  queue    │  TextInjector        │
│  ↓ deque[bytes]     │ ──────►  │  SpellCorrector      │
│  SpeechRecognizer   │           │                      │
│  RMS C extension    │           └──────────────────────┘
└─────────────────────┘

┌─────────────────────────┐
│  model-load thread      │  ← starts at launch, loads 14s model in bg
│  SpeechRecognizer       │
│  SpellCorrector         │
│  TextInjector           │
└──────┬──────────────────┘
       │ GLib.idle_add → auto-start listening when ready
```

**Key design decisions:**

- **SPSC deque** replaces `queue.Queue` for audio chunks — 3–4× lower latency, no GIL mutex overhead
- **C RMS** (`src/c_ext/rms.c`) — single-pass `int16` energy calculation in gcc-O3 C, eliminates NumPy `float64` allocation every 100ms
- **Settings cache** — `silence_threshold` and `silence_duration` captured once at `start_listening()`, not re-read per audio chunk
- **Injection decoupling** — `_injection_thread` absorbs ydotool subprocess latency so recognition never stalls on typing
- **OSD rate-limit** — `update_osd()` only called when text or level changes by >5%, eliminating unnecessary GTK marshaling

---

## ⚡ Performance

| Component | Before | After | Win |
|-----------|--------|-------|-----|
| RMS energy calc | NumPy `float64` alloc | C single-pass `int16` | 2× faster, 0 allocs |
| Audio buffer | `queue.Queue` (mutex) | `deque(maxlen=50)` SPSC | 3–4× lower latency |
| Whisper buffer | `bytes +=` O(N²) growth | `deque[bytes]` + single concat | O(1) append |
| Settings reads | ~20 `dict.get()` / sec | Cached at session start | Eliminated |
| OSD updates | Every audio chunk | Rate-limited on change | ~10 fewer GTK calls/sec |
| Startup visible | **~18 seconds blocked** | **~0.5 seconds** (model loads in bg) | 36× faster |

---

## 🎙️ Speech Engines

### Vosk (Default) — Real-Time Streaming

Vosk uses an offline KALDI acoustic model. Text appears word-by-word as you speak.

```bash
# Default: gigaspeech model (~1.4GB, already downloaded by installer)
# Switch model via Settings → Engine → Vosk Model Path

# Want an alternative model? Download from:
# https://alphacephei.com/vosk/models
```

**Recommended models:**

| Model | Size | Use Case |
|-------|------|----------|
| `vosk-model-en-us-0.22` (gigaspeech) | ~1.4GB | ✅ Default — best accuracy |
| `vosk-model-small-en-us-0.15` | ~40MB | Fast machines / low memory |
| `vosk-model-en-us-0.22-lgraph` | ~128MB | Balanced |

### Whisper — High Accuracy, Punctuated Output

Whisper produces punctuated, capitalized text. Slower (processes in silence-bounded chunks) but significantly more accurate for complex speech.

```bash
# Enable in Settings → Engine → Whisper
# GPU detected automatically (CUDA/ROCm)
```

**Model sizes:**

| Size | VRAM | Notes |
|------|------|-------|
| `tiny` | ~300MB | Fastest, lowest accuracy |
| `base` | ~500MB | Good balance |
| `large-v3-turbo` | ~3GB | SOTA — best for GPU machines |
| `distil-large-v3` | ~1.5GB | Distilled SOTA |

**GPU fallback:** If CUDA isn't available, Whisper runs on CPU. Check `logs/voxinput_logging.db` for device confirmation.

---

## ⚙️ Configuration

Settings are stored in `~/.config/voxinput/settings.json` (or `settings.json` in the project root).

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `speech_engine` | `"Vosk"` | `"Vosk"` or `"Whisper"` |
| `silence_duration` | `0.6` | Seconds of silence to trigger finalization |
| `silence_threshold` | `500` | RMS level below which audio is considered silence |
| `stability_lag` | `2` | Words held back to prevent Vosk word-change flicker |
| `fast_mode` | `false` | Sets `stability_lag=0` for instant output |
| `spell_correction` | `true` | SymSpellPy + ASR artifact post-processing |
| `voice_punctuation` | `true` | Converts "period", "comma", "new line" to symbols |
| `mic_volume` | `100` | PulseAudio input volume (50–150%) |
| `noise_suppression` | `false` | WebRTC `module-echo-cancel` via PulseAudio |

### Tuning for Your Environment

**Noisy room:** Raise `silence_threshold` to 800–1200 so background noise doesn't trigger dictation.

**Fast typist:** Lower `silence_duration` to 0.3s for snappier commit on each phrase.

**Real-time coding:** Enable `fast_mode` + Vosk for instant word-by-word output with zero lag.

---

## 📁 Project Structure

```
VoxInput/
├── install.sh              # One-command installer (idempotent)
├── run.py                  # Entry point
├── src/
│   ├── main.py             # VoxInputApp — orchestrates all threads
│   ├── ui.py               # GTK3: SystemTrayApp, SettingsDialog, OSDOverlay
│   ├── audio.py            # AudioCapture — PyAudio + SPSC deque
│   ├── recognizer.py       # SpeechRecognizer — Vosk / faster-whisper
│   ├── injection.py        # TextInjector — ydotool (Wayland) / xdotool (X11)
│   ├── spell_corrector.py  # SpellCorrector — SymSpellPy + ASR rules
│   ├── mic_enhancer.py     # MicEnhancer — PulseAudio volume/noise controls
│   ├── settings.py         # SettingsManager — JSON persistence
│   ├── config.py           # Constants and paths
│   ├── logger.py           # Enterprise logging — SQLite black-box at TRACE
│   └── c_ext/
│       ├── rms.c           # C RMS extension — single-pass int16 energy
│       ├── build.sh        # gcc -O3 build script
│       └── __init__.py     # ctypes loader + numpy fallback
├── assets/
│   ├── icon_idle.svg
│   └── icon_active.svg
├── bin/
│   ├── gate_check.sh       # CI gate runner (Gate 0–4)
│   └── toggle.sh           # GNOME custom shortcut handler
└── tests/
    ├── unit/               # 72 pytest unit tests (Gates 0 + 4)
    └── fixtures/
        └── golden/         # Golden reference transcripts
```

---

## 🧪 Testing

VoxInput uses a tiered gate system:

```bash
# Gate 0 — Full unit regression (~4s)
bash bin/gate_check.sh 0

# Gate 4 — Performance benchmarks (C ext, deque, latency)
bash bin/gate_check.sh 4

# Run all tests directly
source venv/bin/activate && pytest tests/unit/ -v
```

| Gate | Tests | Covers |
|------|-------|--------|
| Gate 0 | 72 unit tests | All modules, no GTK |
| Gate 4 | 13 perf benchmarks | C RMS speed, O(1) deque, settings cache |

---

## 🔧 Troubleshooting

### Hotkey Not Working

```bash
# Re-run installer to re-register the shortcut
./install.sh

# Or manually set in GNOME:
# Settings → Keyboard → Custom Shortcuts
# Command: bash /path/to/VoxInput/bin/toggle.sh
# Shortcut: Super+Shift+V
```

### Text Not Typing (Wayland)

ydotool requires access to the `uinput` kernel device:

```bash
sudo usermod -aG input $USER
# Then log out and back in
```

### Common Issues

| Problem | Solution |
|---------|----------|
| App doesn't start | Check `logs/voxinput_logging.db` for errors |
| Tray icon missing | GNOME: install `gnome-shell-extension-appindicator` |
| Wrong microphone | Settings → Audio tab → select correct device |
| Typing in wrong window | Click the target window first, then dictate |
| GPU not used (Whisper) | Install CUDA-compatible PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu118` |

---

## 🛠️ Development

```bash
# Clone and set up
git clone https://github.com/bdavidriggins/VoxInput.git
cd VoxInput
./install.sh --no-model   # Skip model download for dev

# Activate venv
source venv/bin/activate

# Run
python3 run.py

# Run tests
pytest tests/unit/ -v

# Build C extension manually
bash src/c_ext/build.sh
```

### Environment Variables (`.env`)

```bash
LOG_LEVEL=TRACE        # TRACE|DEBUG|INFO|WARNING|ERROR
LOG_FILE=logs/voxinput_logging.db
```

Copy `.env.example` → `.env` to customize.

---

## 📦 Installing on Another Machine

```bash
# 1. Clone repo
git clone https://github.com/bdavidriggins/VoxInput.git
cd VoxInput

# 2. Run installer (downloads model automatically)
./install.sh

# 3. Launch from desktop icon or app menu
```

The installer is fully idempotent — safe to re-run for updates.

---

## 🤝 Contributing

PRs are welcome. Some areas where contributions would be great:

- **New ASR artifact rules** in `spell_corrector.py` — common Vosk/Whisper transcription errors
- **Voice commands** — "delete that", "undo", etc.
- **Engine plugins** — Coqui, Nemo, or other offline ASR backends
- **Wayland native input** — replace ydotool subprocess with direct `libinput` or `wlroots` protocol
- **macOS port** — the architecture is OS-agnostic below the injection layer

```bash
git checkout -b feature/my-feature
# make changes
pytest tests/unit/          # must pass Gate 0
git commit -m "feat: description"
git push origin feature/my-feature
# open a PR
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

<div align="center">

Built for the Linux desktop. Inspired by the belief that your voice is your data.

⭐ **Star this repo** if VoxInput saves you from RSI or just makes your workflow cooler.

</div>