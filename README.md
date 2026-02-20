<div align="center">

<img src="assets/icon_active.svg" width="96" alt="VoxInput Logo"/>

# VoxInput

**Privacy-first, offline voice dictation for Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](docs/CONTRIBUTING.md)

*Dictate text into any application using your voice. 100% offline. 100% private.*

[**Quick Start**](#-quick-start) • [**Features**](#-features) • [**Architecture**](#-architecture) • [**Settings**](#-settings-reference) • [**Contributing**](#-contributing)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **Privacy-First** | All processing happens locally. No internet required. No data leaves your machine. |
| ⚡ **Real-Time** | Text appears as you speak via the Vosk streaming engine |
| 🎯 **Universal** | Works in any text field — browsers, terminals, editors, chat apps |
| ⌨️ **Global Hotkey** | Toggle with `Super+Shift+V` from anywhere |
| 🔄 **Dual Engines** | Vosk (fast, streaming) or Whisper (accurate, punctuated) |
| ✨ **Smart Correction** | SymSpell post-processing fixes ASR errors (`teh→the`, `adn→and`) |
| 📖 **Protected Words** | SQLite database of 1,400+ tech/AI/Linux terms that are never corrected |
| 🎙️ **Mic Enhancement** | Noise suppression, gain control, auto-calibration |
| 📊 **Live OSD** | Floating waveform overlay shows dictation in real-time |
| 🔍 **Trace Logging** | Full SQLite black-box log of every recognition event |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required system packages
sudo apt install python3-venv python3-gi python3-gi-cairo \
                 gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 \
                 portaudio19-dev xdotool ydotool
```

### Install

```bash
git clone https://github.com/BigRigVibeCoder/VoxInput.git
cd VoxInput
bash install.sh
```

The installer:
1. Creates a Python virtualenv and installs all dependencies
2. Downloads the Vosk English model (~50MB)
3. Seeds the protected-words database with 1,400+ tech/AI/developer terms
4. Installs a desktop entry and tray icon
5. Auto-starts VoxInput on login (optional)

### Launch

```bash
python3 run.py        # CLI
# OR click the VoxInput icon in your app launcher
```

---

## 🏗️ Architecture

```
VoxInput
├── run.py                  # Entry point + singleton lock
├── src/
│   ├── main.py             # VoxInputApp orchestrator
│   ├── audio.py            # PyAudio capture (16kHz mono)
│   ├── recognizer.py       # Vosk / Whisper engine abstraction
│   ├── spell_corrector.py  # SymSpell + ASR rules + WordDB passthrough
│   ├── word_db.py          # SQLite protected-words DB (in-memory set)
│   ├── injection.py        # xdotool / ydotool text injection
│   ├── mic_enhancer.py     # Noise gate, AGC, calibration
│   ├── ui.py               # GTK3 tray app + Settings dialog + OSD
│   ├── logger.py           # Enterprise SQLite trace logger
│   └── settings.py         # JSON settings manager
├── data/
│   ├── seed_words.py       # 1,400+ initial protected-word seed dataset
│   └── custom_words.db     # SQLite protected words (auto-created, gitignored)
├── assets/
│   ├── icon_idle.svg
│   └── icon_active.svg
├── docs/
│   ├── CONTRIBUTING.md
│   ├── PHANTOM.md          # Feature spec: Phantom Signal v2
│   └── VX-FED-001.md       # Feature spec: Federated dictation
└── tests/
```

### Speech Pipeline

```
Microphone
    ↓ PyAudio (16kHz, mono, float32)
    ↓ RMS level meter (C extension)
MicEnhancer (noise gate + AGC)
    ↓
SpeechRecognizer (Vosk streaming OR Whisper batch)
    ↓ raw text
SpellCorrector
    ├── ASR artifact rules  (gonna→going\ to,  woulda→would\ have…)
    ├── WordDatabase check  (O(1) set lookup — never correct protected words)
    └── SymSpell lookup     (edit-distance ≤ 2, frequency-ranked)
    ↓ corrected text
TextInjector (xdotool type / ydotool type)
    ↓
Active window receives text ✓
```

---

## ⚙️ Settings Reference

Open with `Super+Shift+V` → tray icon → **Settings**, or right-click the tray icon.

### 🎤 Audio Tab
| Setting | Description |
|---------|-------------|
| Input Device | Microphone selection |
| Mic Test | Record + playback to verify input |
| Noise Suppression | WebRTC-style noise gate |
| Gain | Input amplification (0.5–4.0×) |
| Auto-Calibrate | Set noise floor from ambient sample |

### 🧠 Engine Tab
| Setting | Description |
|---------|-------------|
| Engine | `vosk` (real-time) or `whisper` (accurate) |
| Whisper Model | tiny / base / small / medium / large |
| Vosk Model Path | Path to unpacked Vosk model directory |
| Silence Threshold | Seconds of silence before finalizing phrase |
| Speed Mode | `fast` skips spell correction for lowest latency |

### ✏️ Processing Tab
| Setting | Description |
|---------|-------------|
| Spell Correction | Enable/disable SymSpell post-processing |
| Voice Punctuation | Say "period", "comma", "new line" to insert punctuation |

### 📖 Words Tab *(new)*
Browse, search, add, and remove entries in the **Protected Words** database.

- Words in this list are **never spell-corrected** — passed through exactly as spoken
- Ships with **1,400+ seed words**: tech abbreviations, AI/ML terms, Linux distros & tools, developer frameworks, brands, US places & names, Agile/Scrum vocabulary, futurist/emerging tech
- **Search** the list by word or category
- **Add** a word → choose category → Enter or click ➕ Add
- **Remove** — select a row → click 🗑️ Remove
- Changes take effect **immediately** (no restart needed)
- Database is stored in `data/custom_words.db` (SQLite, WAL mode, in-memory for O(1) lookups)

---

## 📖 Protected Words Database

The spell corrector uses a two-pass approach:

1. **SymSpell** — ultra-fast edit-distance dictionary lookup (1M+ words/sec)
2. **WordDatabase** — SQLite-backed exclusion list loaded into a `set[str]` at startup

Words in the database are never corrected, regardless of what SymSpell suggests.

### Seed Categories

| Category | Examples |
|----------|---------|
| `tech` | `api`, `cuda`, `ebpf`, `rag`, `llm`, `grpc`, `wasm` |
| `ai` | `pytorch`, `huggingface`, `ollama`, `vllm`, `qlora`, `dspy`, `langgraph` |
| `linux` | `systemd`, `ebpf`, `btrfs`, `hyprland`, `flatpak`, `pipewire`, `nftables` |
| `dev` | `pydantic`, `fastapi`, `tokio`, `duckdb`, `qdrant`, `prisma`, `drizzle` |
| `cloud` | `terraform`, `argocd`, `eks`, `gke`, `cloudflare`, `fly`, `hetzner` |
| `agile` | `scrum`, `kanban`, `retrospective`, `tdd`, `bdd`, `cqrs`, `asyncio` |
| `org` | `nasa`, `darpa`, `ietf`, `cncf`, `deepmind`, `openai` |
| `future` | `mamba`, `rwkv`, `lerobot`, `qiskit`, `neuromorphic`, `crewai` |
| `name` | 200+ common American first names |
| `place` | All 50 US states + major cities |
| `sports` | All NFL, NBA, MLB teams + sports terms |

### Adding Your Own Words

**Via UI:** Settings → 📖 Words tab → type word → select category → ➕ Add

**Via terminal (bulk):**
```bash
cd VoxInput && source venv/bin/activate
python3 -c "
from src.word_db import WordDatabase
db = WordDatabase('data/custom_words.db')
for word in ['mycompany', 'myproject', 'myname']:
    db.add_word(word, 'custom')
print(db.count(), 'words protected')
"
```

---

## 🔧 Singleton & Desktop Integration

VoxInput uses `fcntl.flock()` on `/tmp/voxinput.lock` to prevent duplicate instances.
Clicking the desktop icon while VoxInput is already running shows a notification instead of launching again.

The desktop entry is installed to:
- `~/.local/share/applications/voxinput.desktop`
- `~/Desktop/voxinput.desktop`

---

## 🔒 Privacy & Security

- **Zero network calls** — all ASR runs locally via Vosk/Whisper
- **No telemetry** — trace logs stay in `logs/voxinput_logging.db` on your machine
- **`.env`** — API keys (if any) stored locally, gitignored
- **`settings.json`** — gitignored; use `settings.example.json` as template
- **`data/custom_words.db`** — gitignored; your word list stays local

---

## 🤝 Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

```bash
# Dev setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit/ -v
```

**Good first issues:** additional seed words, new ASR correction rules, Wayland injection improvements, Whisper VAD integration.

---

## 📄 License

MIT © [BigRigVibeCoder](https://github.com/BigRigVibeCoder)