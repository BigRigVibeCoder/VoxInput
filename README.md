<div align="center">

<img src="assets/icon_active.svg" width="96" alt="VoxInput Logo"/>

# VoxInput

**Privacy-first, offline voice dictation for Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](docs/CONTRIBUTING.md)

*Dictate text into any application using your voice. 100% offline. 100% private.*

[**Quick Start**](#-quick-start) • [**Features**](#-features) • [**Tech Stack**](#-technology-stack) • [**Architecture**](#-architecture) • [**Settings**](#-settings-reference) • [**Contributing**](#-contributing)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **Privacy-First** | All processing happens locally. No internet required. No data leaves your machine. |
| ⚡ **Real-Time Streaming** | Text appears as you speak — Vosk delivers partial results with sub-200ms latency |
| 🎯 **Universal Injection** | Works in any text field — browsers, terminals, editors, chat apps, IDEs |
| ⌨️ **Global Hotkey** | Toggle with `Super+Shift+V` from anywhere via `pynput` |
| 🎙️ **Push-to-Talk** | Hold a configurable key (default: Right Ctrl) — speak — release to inject. Full utterance captured. |
| 🔄 **Dual ASR Engines** | Vosk (fast, streaming) or OpenAI Whisper (accurate, GPU-accelerated) |
| 🧠 **Smart NLP Pipeline** | Compound corrections + SymSpell + ASR rules + numbers + grammar + homophones |
| 📖 **Custom Dictionary** | SQLite DB of 1,400+ tech/AI/Linux terms — injected into SymSpell as correction *targets* |
| 🔗 **Compound Corrections** | DB-driven multi-word ASR correction: `"pie torch"→PyTorch`, `"engine next"→nginx` (35 defaults, user-extensible) |
| 🎙️ **Three Noise Engines** | WebRTC AEC, RNNoise AI denoiser, or EasyEffects — pick your fighter |
| 🔊 **Voice Punctuation** | Say "period", "comma", "new paragraph" — supports cross-batch buffering |
| 🔢 **Number Intelligence** | "one hundred twenty three" → `123`, "twenty first" → `21st` |
| 📊 **Live OSD** | Floating waveform overlay shows dictation state in real-time |
| 🏎️ **C Extension** | Native `librms.so` — zero-Python-overhead RMS + PCM→float32 conversion |
| 🖥️ **Hardware Auto-Tune** | Detects CPU/RAM/GPU at startup and auto-selects optimal engine settings |
| 🔍 **Flight Recorder** | Enterprise SQLite black-box logger with TRACE level + crash artifacts |
| 🖱️ **Tray App + Desktop** | GTK3 system tray with full settings dialog, mic test, and desktop icon |
| 🎯 **Golden Test Suite** | Record once, test forever — WER accuracy regression testing with 6 test paragraphs |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Ubuntu/Debian — required system packages
sudo apt install python3-venv python3-gi python3-gi-cairo \
                 gir1.2-gtk-3.0 gir1.2-appindicator3-0.1 \
                 portaudio19-dev xdotool

# Optional (for Wayland-native injection)
sudo apt install ydotool

# Optional (for RNNoise AI denoiser)
sudo apt install libladspa-ocaml-dev
# or install noise-suppression-for-voice from GitHub
```

### Install

```bash
git clone https://github.com/BigRigVibeCoder/VoxInput.git
cd VoxInput
bash install.sh
```

The installer:
1. Creates a Python virtualenv and installs all dependencies (~50 packages)
2. Compiles the C RMS extension (`librms.so`) with `-O3 -march=native`
3. Downloads the Vosk English model (~50MB)
4. Seeds the protected-words database with 1,400+ tech/AI/developer terms
5. Installs a `.desktop` entry and tray icon system-wide
6. Configures optional auto-start on login

### Launch

```bash
python3 run.py                   # CLI
# OR click the VoxInput icon in your app launcher / desktop
# OR toggle with Super+Shift+V
```

### Verify Installation

```bash
# Run the unit test suite
source venv/bin/activate
pytest tests/unit/ -v
```

---

## 🔧 Technology Stack

### Core Speech Engines

| Technology | Role | Details |
|-----------|------|---------|
| **[Vosk](https://alphacephei.com/vosk/)** | Primary ASR engine | Offline Kaldi-based, real-time streaming, ~50MB model |
| **[OpenAI Whisper](https://github.com/openai/whisper)** | Alternate ASR engine | GPU-accelerated (CUDA float16/int8), auto-punctuation |
| **[SymSpell](https://github.com/wolfgarbe/SymSpell)** | Spell correction | 1M+ words/sec edit-distance lookup, frequency-ranked |

### Audio Pipeline

| Technology | Role | Details |
|-----------|------|---------|
| **[PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)** | Audio capture | 16kHz mono, int16 PCM via PortAudio bindings |
| **librms.so** (C) | RMS + PCM conversion | Custom ctypes extension — zero Python overhead |
| **[PulseAudio](https://www.freedesktop.org/wiki/Software/PulseAudio/)** / **PipeWire** | Device management | `pactl` for source enumeration, volume, default device |
| **WebRTC AEC** | Noise suppression | PulseAudio `module-echo-cancel` with 5 tunable sub-features |
| **[RNNoise](https://jmvalin.ca/demo/rnnoise/)** | AI denoiser | LADSPA plugin via `module-ladspa-source` |
| **[EasyEffects](https://github.com/wwmm/easyeffects)** | Advanced audio DSP | Optional GUI-based effects chain launcher |

### Text Processing

| Technology | Role | Details |
|-----------|------|---------|
| **ASR Rules Engine** | Artifact correction | `gonna→going to`, `woulda→would have`, 20+ substitution rules |
| **Number Parser** | Spoken→numeric | Handles cardinals, ordinals, scales (`one hundred→100`, `twenty first→21st`) |
| **Homophone Resolver** | Context-aware fixes | Regex-based: `their/there/they're`, `to/too/two`, `its/it's`, `your/you're`, `then/than`, `affect/effect` |
| **Grammar Engine** | Sentence structure | Auto-capitalization, cross-batch state tracking |
| **[SQLite](https://sqlite.org/)** | Protected words DB | In-memory `set[str]` for O(1) lookups, WAL mode, 1,400+ seed terms |

### Desktop Integration

| Technology | Role | Details |
|-----------|------|---------|
| **[GTK3](https://docs.gtk.org/gtk3/)** (`gi`) | UI framework | System tray, settings dialog, OSD waveform overlay |
| **[AppIndicator3](https://lazka.github.io/pgi-docs/AppIndicator3-0.1/)** | Tray icon | Idle/active SVG state icons |
| **[pynput](https://pynput.readthedocs.io/)** | Global hotkey | `Super+Shift+V` keyboard listener |
| **xdotool** / **ydotool** | Text injection | X11 and Wayland-native keystroke simulation |
| **pynput** (fallback) | Text injection | Pure-Python X11 fallback when neither tool is available |
| **fcntl** | Singleton lock | `/tmp/voxinput.lock` — prevents duplicate instances |

### Observability

| Technology | Role | Details |
|-----------|------|---------|
| **SQLite** | Flight recorder | `logs/voxinput_logging.db` — every event, batched writes, auto-trim |
| **TRACE level** (5) | High-frequency logging | Custom level below DEBUG for audio loop events |
| **Crash artifacts** | Post-mortem | `crash_artifacts` table with stack traces + system state snapshots |
| **`sys.excepthook`** | Root handler | Catches all unhandled exceptions, writes crash artifact before exit |

### Hardware Intelligence

| Component | Detection | Impact |
|-----------|-----------|--------|
| **CPU cores** | `psutil` / `os.cpu_count()` | Vosk chunk size: 100ms (8+ cores), 150ms (4+), 200ms (2) |
| **RAM** | `psutil` / `/proc/meminfo` | Memory-aware model selection |
| **GPU (CUDA)** | `torch.cuda` / `nvidia-smi` | Whisper backend: `cuda/float16` (≥4GB), `cuda/int8` (≥2GB), `cpu/int8` (fallback) |

---

## 🏗️ Architecture

```
VoxInput/
├── run.py                      # Entry point, singleton lock, stale-process cleanup
├── src/
│   ├── main.py                 # VoxInputApp orchestrator (4 threads)
│   ├── audio.py                # PyAudio capture (16kHz mono int16)
│   ├── recognizer.py           # Vosk / Whisper engine abstraction
│   ├── spell_corrector.py      # SymSpell + ASR rules + numbers + grammar
│   ├── homophones.py           # Context-aware homophone resolver (regex-based)
│   ├── word_db.py              # SQLite protected-words DB (in-memory set)
│   ├── injection.py            # xdotool / ydotool / pynput text injection
│   ├── mic_enhancer.py         # WebRTC / RNNoise / EasyEffects / auto-calibrate
│   ├── pulseaudio_helper.py    # PulseAudio/PipeWire source enumeration
│   ├── hardware_profile.py     # CPU / RAM / GPU auto-detection (singleton)
│   ├── ui.py                   # GTK3 tray + settings dialog + OSD overlay
│   ├── config.py               # App constants (paths, hotkey, sample rate)
│   ├── settings.py             # JSON settings manager
│   ├── logger.py               # Enterprise SQLite flight recorder
│   └── c_ext/
│       ├── rms.c               # Fast RMS + PCM→float32 (gcc -O3)
│       ├── librms.so           # Compiled shared library
│       └── __init__.py         # ctypes bindings
├── data/
│   ├── seed_words.py           # 1,400+ initial protected-word seed dataset
│   └── custom_words.db         # SQLite protected words (auto-created, gitignored)
├── assets/
│   ├── icon_idle.svg           # Tray icon: idle state
│   └── icon_active.svg         # Tray icon: listening state
├── bin/
│   ├── toggle.sh               # SIGUSR1 toggle script for hotkey binding
│   ├── gate_check.sh           # Pre-commit quality gate
│   └── ...                     # Benchmarking and packaging tools
├── tests/                      # Unit, integration, and E2E test suite
├── docs/                       # CONTRIBUTING.md, feature specs
└── logs/                       # SQLite flight recorder database
```

### Speech Pipeline

```
Microphone
    ↓ PyAudio (16kHz, mono, int16)
    ↓ librms.so — C native RMS level measurement
MicEnhancer
    ├── WebRTC AEC (noise gate + AGC + VAD + high-pass)
    ├── RNNoise AI denoiser (LADSPA plugin)
    └── EasyEffects (external DSP chain)
    ↓
SpeechRecognizer
    ├── Vosk: real-time streaming, partial results every 100–200ms
    └── Whisper: batch mode, GPU-accelerated (CUDA float16/int8)
    ↓ raw words  (PTT mode: buffered until key release)
VoicePunctuationBuffer
    ↓ cross-batch command assembly ("new" + "line" → "\n")
SpellCorrector
    ├── 0. Compound corrections (DB: "pie torch"→PyTorch, "engine next"→nginx)
    ├── 1. ASR artifact rules  (gonna→going to, woulda→would have…)
    ├── 2. Number parser       (one hundred twenty three → 123)
    ├── 3. WordDatabase check  (O(1) set lookup — never correct protected words)
    ├── 4. SymSpell lookup     (edit-distance ≤ 2, custom words injected at 1M frequency)
    └── 5. Grammar engine      (auto-capitalize, sentence tracking)
    ↓ corrected text
HomophoneResolver
    ↓ context-aware fixes (their/there/they're, to/too/two…)
TextInjector (ydotool → xdotool → pynput)
    ↓
Active window receives text ✓
```

### Threading Model

| Thread | Responsibility |
|--------|---------------|
| **GTK Main** | UI rendering, tray icon, settings dialog, OSD |
| **Audio Capture** | PyAudio callback → queue (real-time priority) |
| **Process Loop** | Recognizer → SpellCorrector → homophone → injection queue |
| **Injection Loop** | Drains queue → xdotool/ydotool keystroke simulation |

---

## ⚙️ Settings Reference

Open with `Super+Shift+V` → tray icon → **Settings**, or right-click the tray icon.

### 🎤 Dictation Mode Tab
| Setting | Description |
|---------|-------------|
| Mode | **Always On** (toggle with hotkey) or **Push-to-Talk** (hold key to speak) |
| PTT Key | Configurable keybind — click "Record Key" and press any key/combo |
| PTT Behavior | Hold to record → release to process full utterance → inject text |

### 🎤 Audio Tab
| Setting | Description |
|---------|-------------|
| Input Device | PulseAudio/PipeWire source selection |
| Mic Test | Record + playback to verify input quality |
| Noise Suppression | WebRTC AEC with 5 sub-toggles (noise gate, HF filter, VAD, analog/digital gain) |
| RNNoise | AI-powered noise suppression via LADSPA plugin |
| EasyEffects | Launch external DSP effects chain |
| Gain | Input amplification (0.5–4.0×) |
| Auto-Calibrate | Sample ambient noise floor → set threshold + volume automatically |

### 🧠 Engine Tab
| Setting | Description |
|---------|-------------|
| Engine | `Vosk` (real-time streaming) or `Whisper` (accurate, GPU) |
| Vosk Model | Dropdown model selector with validation |
| Whisper Model | tiny / base / small / medium / large |
| Silence Threshold | Seconds of silence before finalizing phrase |
| Speed Mode | `fast` skips spell correction for lowest latency |

### ✏️ Processing Tab
| Setting | Description |
|---------|-------------|
| Spell Correction | Enable/disable SymSpell post-processing |
| Voice Punctuation | Say "period", "comma", "new line" to insert punctuation |
| Homophone Correction | Context-aware their/there/they're, to/too/two fixes |
| Number Parsing | Convert spoken numbers to digits (one hundred → 100) |

### 📖 Words Tab
Browse, search, add, and remove entries in the **Protected Words** database.

- Words in this list are **never spell-corrected** — passed through exactly as spoken
- Custom words are **injected into SymSpell** as high-frequency correction targets (1M)
- Ships with **1,400+ seed words**: tech abbreviations, AI/ML terms, Linux distros & tools, developer frameworks, brands, US places & names, Agile/Scrum vocabulary, futurist/emerging tech
- **Search** the list by word or category
- **Add** a word → choose category → Enter or click ➕ Add
- **Remove** — select a row → click 🗑️ Remove
- Changes take effect **immediately** (no restart needed)
- Database is stored in `data/custom_words.db` (SQLite, WAL mode, in-memory for O(1) lookups)

---

## 📖 Protected Words Database

The spell corrector uses a multi-pass approach:

1. **Compound Corrections** — DB-driven multi-word ASR correction (35 defaults, user-extensible)
2. **ASR Rules** — substitution table for common speech-to-text artifacts
3. **Number Parser** — converts spoken numbers to digits with ordinal support
4. **WordDatabase** — SQLite-backed exclusion list loaded into a `set[str]` at startup
5. **SymSpell** — ultra-fast edit-distance dictionary lookup (custom words injected at 1M frequency)
6. **Grammar** — auto-capitalization and sentence state tracking

Words in the database are never corrected, regardless of what SymSpell suggests.
Custom words are also *injected* into SymSpell so misspellings correct *toward* your dictionary terms.

### Compound Corrections

Vosk often splits unknown tech terms into phonetically similar English words:

| Vosk Hears | Corrected To |
|---|---|
| `cooper eighties` | `kubernetes` |
| `pie torch` | `PyTorch` |
| `engine next` | `nginx` |
| `tail scale` | `Tailscale` |
| `rough fauna` | `Grafana` |
| `pincer flow` | `TensorFlow` |
| `and symbol` | `Ansible` |
| `a p i` | `API` |

These are stored in the `compound_corrections` table in `custom_words.db`.
Add your own via terminal:
```bash
python3 -c "
from src.word_db import WordDatabase
db = WordDatabase('data/custom_words.db')
db.add_compound_correction('my misheard phrase', 'CorrectWord')
"
```

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
On launch, stale processes are detected via `pgrep` and cleaned up automatically.
A poll-wait mechanism ensures clean handoff when GNOME fires a double-launch from the desktop icon.

The desktop entry is installed to:
- `~/.local/share/applications/voxinput.desktop`
- `~/Desktop/voxinput.desktop`

---

## 📋 Recent Upgrades

| Version | Change |
|---------|--------|
| **Feb 23** | 🎙️ **Push-to-Talk mode** — hold key to record, release to inject. Full utterance buffering. |
| **Feb 23** | 🔗 **DB-driven compound corrections** — 35 multi-word ASR correction rules in SQLite |
| **Feb 23** | 📊 **SymSpell dictionary injection** — 1,437 custom words as correction *targets* |
| **Feb 23** | 🎯 **Golden Paragraph F** — dictionary test recording + WER regression testing |
| **Feb 23** | Fix GNOME desktop-icon race condition in singleton lock |
| **Feb 22** | RNNoise AI denoiser + EasyEffects launcher + Processing toggles |
| **Feb 22** | Homophone resolver: `their/there/they're`, `to/too/two`, `its/it's`, `your/you're` |
| **Feb 21** | WebRTC sub-feature toggles (5 individual controls) |
| **Feb 20** | Enterprise SQLite flight recorder with TRACE level + crash artifacts |
| **Feb 20** | Performance Overhaul v2.0 — 10 improvements across speed, memory, quality |
| **Feb 19** | Number intelligence: spoken→numeric conversion with ordinals |
| **Feb 19** | Cross-batch voice punctuation buffering |
| **Feb 18** | C extension `librms.so` for zero-overhead RMS computation |
| **Feb 18** | Hardware auto-detection (CPU/RAM/CUDA) with engine tuning |

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

**Good first issues:** additional seed words, new ASR correction rules, Wayland injection improvements, Whisper VAD integration, new homophone groups.

---

## 📄 License

MIT © [BigRigVibeCoder](https://github.com/BigRigVibeCoder)