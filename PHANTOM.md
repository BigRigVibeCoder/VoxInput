# PHANTOM.md
# VoxInput — Phantom Signal Specification
## *The Authoritative Technical Reference for Offline Voice-to-Text on Linux*

> **Document ID**: VX-SPEC-001  
> **Version**: 1.0.0  
> **Status**: Living Document  
> **Last Updated**: 2026-02-20  
> **Project**: [VoxInput](https://github.com/bdavidriggins/VoxInput)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Deep Dive](#2-architecture-deep-dive)
3. [Component Specifications](#3-component-specifications)
4. [Voice-to-Text Engine Analysis](#4-voice-to-text-engine-analysis)
5. [Audio Pipeline](#5-audio-pipeline)
6. [Text Injection System](#6-text-injection-system)
7. [UI & System Tray](#7-ui--system-tray)
8. [Settings & Configuration](#8-settings--configuration)
9. [Hotkey & Signal Architecture](#9-hotkey--signal-architecture)
10. [Testing Infrastructure](#10-testing-infrastructure)
11. [Deployment & Packaging](#11-deployment--packaging)
12. [Code Review Findings](#12-code-review-findings)
13. [Known Limitations & Technical Debt](#13-known-limitations--technical-debt)
14. [Roadmap Recommendations](#14-roadmap-recommendations)

---

## 1. Project Overview

VoxInput is a **100% offline, privacy-first voice-to-text dictation tool** for Linux desktops. It operates as a GNOME system tray application that captures microphone audio, transcribes it using a local speech recognition engine (Vosk or Whisper), and injects the resulting text into whatever application has keyboard focus — with no data ever leaving the machine.

### Core Design Philosophy

| Pillar | Implementation |
|--------|----------------|
| **Offline First** | All ML inference runs locally; no network calls during operation |
| **Universal Input** | Text injection works in any X11 application via `xdotool` |
| **Zero-Friction UX** | Single hotkey (`Win+Shift+V`) for start/stop; system tray presence |
| **Dual Engine** | Vosk (fast, streaming) or Whisper (accurate, batched) selectable at runtime |
| **Privacy Absolute** | No telemetry, no logging to external services, no cloud dependency |

### Version History

| Version | Status | Notes |
|---------|--------|-------|
| `v1.0.0` | Current | Initial public release. Vosk + Whisper engines. GNOME integration. |

---

## 2. Architecture Deep Dive

### 2.1 High-Level System Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION LAYER                        │
│                                                                        │
│   Win+Shift+V ──► toggle.sh ──► SIGUSR1 signal ──► VoxInputApp        │
│                        └─► Launch app if not running                  │
│                                                                        │
│   GTK3 System Tray ◄──► SystemTrayApp ◄──► VoxInputApp.toggle()       │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       APPLICATION CORE (main.py)                      │
│                                                                        │
│                        VoxInputApp                                     │
│                    ┌──────┼──────────┐                                │
│                    │      │          │                                 │
│                    ▼      ▼          ▼                                 │
│            AudioCapture  SpeechRecognizer  TextInjector                │
│                    │      │          │                                 │
│                    │      ├─ Vosk    │                                 │
│                    │      └─ Whisper │                                 │
│                    │                │                                  │
│            SettingsManager ◄────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
                        │               │
                        ▼               ▼
┌───────────────────┐  ┌──────────────────────────────────────┐
│  AUDIO SUBSYSTEM  │  │        TEXT OUTPUT SUBSYSTEM          │
│                   │  │                                       │
│  PulseAudio /     │  │  xdotool type --clearmodifiers        │
│  PipeWire         │  │      └─► Fallback: pynput.Controller  │
│  (via pactl)      │  │                                       │
│       │           │  └──────────────────────────────────────┘
│       ▼           │
│  PyAudio stream   │
│  16kHz, 16-bit    │
│  mono, 8000-frame │
│  chunks           │
└───────────────────┘
```

### 2.2 Processing Pipeline

```
MIC ──► PyAudio queue ──► _process_loop thread
                                │
                                ├─ audioop.rms() ──► Silence Detection
                                │       │
                                │       ├─ rms < threshold → silence timer
                                │       │         └─ timeout > duration → finalize()
                                │       └─ rms >= threshold → reset timer
                                │
                                └─ recognizer.process_audio(data)
                                        │
                                        ├──[Vosk] AcceptWaveform()
                                        │     ├─ Full result → inject remaining words
                                        │     └─ Partial → Lag-N stabilization → inject stable prefix
                                        │
                                        └──[Whisper] rolling buffer accumulation
                                              ├─ throttle: 500ms interval
                                              ├─ min buffer: 1 second of audio
                                              ├─ transcribe() → word diff vs committed
                                              └─ Lag-N stabilization → inject stable words
                                                        └─ finalize() on silence (LAG=0)
                                        │
                                        ▼
                                TextInjector.type_text(words)
                                        ├─ xdotool type --clearmodifiers --delay 0 "text "
                                        └─ fallback: pynput.keyboard.Controller.type()
```

### 2.3 Threading Model

| Thread | Name | Responsibility |
|--------|------|----------------|
| Main (GTK) | `Gtk.main()` | UI event loop, signal handling |
| Processing | `_process_loop` | Audio dequeue → recognize → inject |
| PyAudio callback | `_callback` | Audio capture (hardware callback, enqueues data) |
| Test playback | `_play_playback` | Mic test audio playback (temporary, transient) |

> **GTK Thread Safety**: All UI updates from non-main threads use `GLib.idle_add()`. Direct GTK method calls from the processing thread are **avoided** — this is correctly implemented.

---

## 3. Component Specifications

### 3.1 Module Map

```
VoxInput/
├── run.py                     # Entry point (runpy.run_module wrapper)
├── src/
│   ├── __init__.py
│   ├── main.py                # VoxInputApp — master orchestrator
│   ├── recognizer.py          # SpeechRecognizer — dual-engine STT
│   ├── audio.py               # AudioCapture — PyAudio stream manager
│   ├── injection.py           # TextInjector — xdotool/pynput output
│   ├── ui.py                  # SystemTrayApp + SettingsDialog (GTK3)
│   ├── pulseaudio_helper.py   # PulseAudio/PipeWire device enumeration
│   ├── config.py              # Compile-time constants
│   ├── settings.py            # SettingsManager — singleton JSON store
│   └── [audio|injection|recognition|ui|utils]/  # Empty stub dirs (future)
├── tests/
│   ├── conftest.py            # Global mock fixtures (pyaudio, vosk, gi)
│   ├── unit/                  # Unit tests (stub directory)
│   ├── integration/           # Integration tests
│   │   └── test_audio_setup.py
│   └── e2e/                   # E2E tests (stub directory)
├── bin/
│   ├── toggle.sh              # Hotkey handler: launch or SIGUSR1
│   ├── fix_hotkey.sh          # Hotkey repair utility
│   └── create_package.sh      # Release zip builder
├── assets/
│   ├── icon_idle.svg          # Green tray icon
│   └── icon_active.svg        # Red tray icon
├── model/                     # Vosk model directory (auto-downloaded)
├── install.sh                 # One-click installer
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Dev tooling (ruff, mypy, pytest)
├── pyproject.toml             # Tool config (ruff, mypy, pytest)
├── settings.json              # Runtime settings (user-specific)
├── settings.example.json      # Settings template
└── voxinput.desktop           # XDG desktop entry
```

---

## 4. Voice-to-Text Engine Analysis

This is the technical core of VoxInput. Two fundamentally different approaches are implemented under a unified `SpeechRecognizer` interface.

### 4.1 Vosk Engine

**Library**: `vosk` (Kaldi-based, offline ASR)  
**Model**: `vosk-model-small-en-us-0.15` (~40MB default) or custom large model  
**Latency**: ~50-200ms per chunk (real-time capable)  
**Output**: Lowercase text, no punctuation

#### Lag-N Stabilization Strategy

Vosk's `KaldiRecognizer` emits two types of results:

1. **Partial Results**: Emitted continuously as the user speaks. Words near the end of the partial are unstable — Kaldi may revise them as more audio arrives.
2. **Full Results**: Emitted when Kaldi detects an utterance boundary (silence). These are final.

The stabilization algorithm:

```python
# Partial result processing
words = partial_text.split()
stable_len = max(0, len(words) - LAG)   # Hold back last N words
new_words = words[committed_len : stable_len]
committed_text.extend(new_words)
# inject new_words immediately
```

```python
# Full result processing
words = final_text.split()
new_words = words[committed_len:]       # Inject everything uncommitted
committed_text = []                     # Reset for next utterance
```

**Default LAG**: `1` word (configurable, 0-10 range)  
**Trade-off**: LAG=0 = maximum speed but may inject words that get corrected. LAG=2+ = smoother output but adds perceived latency.

#### Model Path Resolution

```python
model_path = self.settings.get("model_path", MODEL_PATH)
if not os.path.exists(model_path):
    if model_path != MODEL_PATH and os.path.exists(MODEL_PATH):
        model_path = MODEL_PATH   # Fallback to default
    else:
        raise FileNotFoundError(...)
```

Supports user-configurable large models (e.g., `vosk-model-en-us-0.22`, ~1.8GB). Model selection is persisted in `settings.json`.

---

### 4.2 Whisper Engine

**Library**: `openai-whisper`  
**Backend**: PyTorch (CUDA GPU preferred, CPU fallback)  
**Model sizes**: `tiny`, `base`, `small`, `medium`, `large`  
**Latency**: 500ms–several seconds (batch processing, not true streaming)  
**Output**: Capitalized text with punctuation (proper sentences)

#### Rolling Buffer Streaming Strategy

Whisper is inherently a batch transcription tool, not a streaming ASR. VoxInput implements a pseudo-streaming approach:

```
Audio data ──► whisper_buffer (byte accumulation)
                    │
                    ├─ Throttle: skip if < 500ms since last inference
                    ├─ Min buffer: skip if < 1 second of audio
                    │
                    ▼
             numpy conversion: int16 → float32 / 32768.0
                    │
                    ▼
             whisper.transcribe(audio_np, fp16=False, beam_size=1, language='en')
                    │
                    ▼
             word diff vs committed_text (Lag-N, default LAG=2)
                    │
                    ├─ Sentence end detected (punctuation) → flush buffer, reset committed
                    └─ inject new stable words
```

**GPU Detection**: `whisper.load_model(size)` will auto-use CUDA if available. On failure, falls back to CPU with a clean warning log entry. Verifiable via `voxinput.log`:

```
INFO - Whisper model loaded successfully on device: cuda:0
```

#### The Whisper Divergence Problem

This is the most significant known limitation, well-documented in the source code:

```python
# If committed: "The quick"
# Current:      "The quick brown"  → Inject "brown"  ✓
# But if:
# Current:      "The thick brown"  → WE HAVE A PROBLEM.
# We already injected "quick" — we cannot delete it.
```

**Current mitigation**: The code accepts the divergence and appends anyway. A "hard fork" of the transcript reality occurs silently. This is an acceptable trade-off for real-time feel, but the user may occasionally see incorrectly injected words that don't get corrected.

#### Silence-Based Finalization

When the main loop detects silence exceeding `silence_duration`, it calls `recognizer.finalize()`:

```python
def finalize(self):
    # Runs Whisper inference with LAG=0 (inject everything remaining)
    # Then flushes buffer entirely
    # Returns any uncommitted terminal words
```

This is Whisper-only. Vosk's Kaldi handles finalization internally via `AcceptWaveform`.

---

### 4.3 Engine Selection & Hot Reload

Engine selection is persisted in `settings.json`. The `reload_engine()` method in `VoxInputApp` supports **live engine switching** without restarting the app:

```python
def reload_engine(self):
    was_listening = self.is_listening
    if was_listening: self.stop_listening()
    self.recognizer = SpeechRecognizer()   # Re-reads settings
    if was_listening: self.start_listening()
```

This also clears GPU memory before reinitializing:
```python
import torch; torch.cuda.empty_cache(); gc.collect()
```

---

## 5. Audio Pipeline

### 5.1 AudioCapture (`audio.py`)

**Library**: PyAudio (PortAudio binding)  
**Format**: `paInt16` (16-bit signed integer PCM)  
**Sample Rate**: `16000 Hz` (required by both Vosk and Whisper)  
**Channels**: `1` (mono)  
**Chunk Size**: `8000 frames` (= 500ms of audio per callback)  

#### Non-Blocking Architecture

PyAudio is opened with `stream_callback`, placing audio capture on a dedicated PortAudio thread. The callback simply enqueues data:

```python
def _callback(self, in_data, frame_count, time_info, status):
    if self.is_running:
        self.queue.put(in_data)
    return (None, pyaudio.paContinue)
```

The processing thread reads from this queue via `get_data()` which returns `None` if empty (non-blocking check). This prevents the processing thread from blocking on audio I/O.

**Potential Issue**: `queue.Queue()` is unbounded. Under heavy load (slow inference), the queue can grow indefinitely. No high-water mark or drop policy is implemented.

### 5.2 PulseAudio Integration (`pulseaudio_helper.py`)

PyAudio only sees ALSA-level devices. Modern Linux uses PulseAudio/PipeWire, which exposes virtual devices (e.g., Easy Effects, Bluetooth headsets) that ALSA alone cannot enumerate.

The helper uses `pactl` subprocess calls to query the audio daemon:

```bash
pactl list sources        # enumerate all sources
pactl get-default-source  # get current default
pactl set-default-source  # set default (called on device change)
```

**Filtering**: Monitor sources (`.monitor` suffix) are excluded — these capture system audio output, not microphone input.

**Timeout**: All `pactl` calls have a 5-second timeout to prevent the UI from hanging if PulseAudio is unresponsive.

### 5.3 Silence Detection (RMS-based)

Silence detection runs in the processing loop alongside recognition:

```python
rms = audioop.rms(data, 2)  # 2 = bytes per sample (16-bit)
if rms < silence_threshold:
    # Start/continue silence timer
    if elapsed > silence_duration:
        recognizer.finalize()  # Force flush
```

**Configurable parameters** (via Settings dialog):
- `silence_threshold`: Volume RMS below which silence is declared (default: 500, range: 0–5000)  
- `silence_duration`: How long silence must persist before finalizing (default: 0.6s, range: 0.1–5.0s)

The `audioop` module is from the Python standard library (deprecated in Python 3.11, removed in 3.13 — see [Code Review Findings](#12-code-review-findings)).

---

## 6. Text Injection System

### 6.1 TextInjector (`injection.py`)

**Primary method**: `xdotool type --clearmodifiers --delay 0 "text "`  
**Fallback**: `pynput.keyboard.Controller.type(text)`

#### Why xdotool over pynput?

| Factor | xdotool | pynput |
|--------|---------|--------|
| Multi-byte character support | Excellent | Good |
| Modifier key handling | `--clearmodifiers` prevents stuck keys | Manual key simulation |
| Reliability under GTK | High | Medium (can conflict with GTK event loop) |
| Availability | Must be installed (`apt install xdotool`) | Python package |

`xdotool` is installed by `install.sh` as a system dependency.

#### Word Spacing

Every injected text batch has a trailing space appended:
```python
full_text = text.strip() + ' '
```

This ensures that successive words are separated when injecting incrementally. It means the last word of a session will have a trailing space — a minor cosmetic issue that users generally don't notice.

#### Backspace Support

A `backspace()` method exists but is **not currently called** by the main processing logic. It was implemented in anticipation of divergence correction for Whisper, which was ultimately deferred.

---

## 7. UI & System Tray

### 7.1 SystemTrayApp

**Toolkit**: GTK3 via GObject Introspection (`gi.repository.Gtk`)  
**Widget**: `Gtk.StatusIcon` (deprecated in GTK4 but stable in GTK3)  
**Icons**: SVG files from `assets/` (idle: green, active: red)

#### Interaction Model

| Action | Result |
|--------|--------|
| Left-click tray icon | Toggle listening |
| Right-click tray icon | Show context menu |
| Menu → "Start/Stop Listening" | Toggle listening |
| Menu → "Settings" | Open SettingsDialog |
| Menu → "Quit" | Graceful shutdown |

The menu item label updates dynamically via `GLib.idle_add` to reflect current state ("Start Listening" ↔ "Stop Listening").

### 7.2 SettingsDialog

A full `Gtk.Dialog` with three sections:

#### Section 1: Audio Input
- Device selector (`Gtk.ComboBoxText`) populated via `pulseaudio_helper`
- Live microphone test: records audio, shows RMS level bar, plays back through speakers
- Device changes trigger `pactl set-default-source` immediately upon save

#### Section 2: Speech Engine
- Engine selector: Vosk or Whisper
- **Vosk**: Folder picker (`Gtk.FileChooserButton`) for model path
- **Whisper**: Model size selector (`tiny` / `base` / `small` / `medium` / `large`)
- Visibility toggles: shows only relevant widgets for selected engine

#### Section 3: Advanced Options
- **Silence Duration**: 0.1–5.0s (spin button, step 0.1)
- **Stability Lag**: 0–10 words (spin button)
- **Mic Noise Threshold**: 0–5000 RMS (spin button, step 100)

#### Settings Persistence

Settings are saved immediately on dialog OK via `SettingsManager.set()`, which writes to `settings.json`. Engine-change trigger fires `engine_change_callback` → `VoxInputApp.reload_engine()` for zero-restart hot reload.

#### Mic Test Feature

The settings dialog includes a functional microphone test:
1. Captures audio from PyAudio at 16kHz
2. Shows real-time level bar (RMS/10000, clamped to 1.0)
3. On stop, plays back the recording through speakers
4. Uses a separate `pyaudio.PyAudio()` instance (independent of main capture)

**Risk**: If the recording fails after opening a stream, `pa` may not be terminated cleanly (mitigated by finally block in `_play_playback`).

---

## 8. Settings & Configuration

### 8.1 SettingsManager (`settings.py`)

**Pattern**: Singleton (via `__new__` override)  
**Storage**: `settings.json` at project root  
**Thread Safety**: No explicit locking — dict reads/writes are GIL-protected but not atomic for multi-key operations

#### Singleton Implementation

```python
class SettingsManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.settings = {}
            cls._instance.load()
        return cls._instance
```

**Critical Bug**: The singleton is module-global. In test contexts, the singleton persists across test cases. `conftest.py` does not reset `SettingsManager._instance = None` between tests. This can cause test pollution if settings are mutated.

### 8.2 config.py — Compile-Time Constants

```python
MODEL_PATH = os.path.join(BASE_DIR, "..", "model")  # Default Vosk model dir
SAMPLE_RATE = 16000                                  # Required by Vosk/Whisper
CHANNELS = 1                                         # Mono
CHUNK_SIZE = 8000                                    # Frames per PyAudio callback
HOTKEY = '<cmd>+<shift>+v'                           # Not used (SIGUSR1 supercedes)
LOG_FILE = os.path.join(BASE_DIR, "..", "voxinput.log")
```

**Note**: `HOTKEY` is defined but the internal `pynput.GlobalHotKeys` listener is **commented out** in `main.py`. The hotkey is handled externally via GNOME custom keybinding → `toggle.sh` → SIGUSR1. The constant is dead code.

### 8.3 settings.json — Default Values

| Key | Default | Override in settings.json |
|-----|---------|--------------------------|
| `speech_engine` | `"Vosk"` | `"Vosk"` |
| `model_path` | `{src}/../model` | `"/home/.../model/gigaspeech"` |
| `whisper_model_size` | `"small"` (in `get()`) | `"base"` |
| `silence_threshold` | `500` | `300` |
| `silence_duration` | `0.6` | `0.2` |
| `stability_lag` | `2` | `4` |
| `audio_device` | system default | Logitech USB headset |

**Inconsistency**: `SettingsManager.get("whisper_model_size")` special-cases `default="small"` but settings.json shows `"base"`. First-launch behavior depends on whether settings.json exists.

---

## 9. Hotkey & Signal Architecture

### 9.1 Signal Flow

```
GNOME Keyboard Shortcut (Super+Shift+V)
        │
        ▼
/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom-voxinput/
        │  binding: <Super><Shift>v
        │  command: /path/to/bin/toggle.sh
        │
        ▼
bin/toggle.sh
        ├─ pgrep -f "run.py"
        │       ├─ RUNNING → pkill -USR1 -f "run.py"  (sends SIGUSR1)
        │       └─ NOT RUNNING → nohup python run.py &  (launches)
        │
        ▼ (if already running)
SIGUSR1 → Python signal handler (registered in VoxInputApp.run())
        │  signal.signal(signal.SIGUSR1, lambda s, f: self.toggle_listening())
        │
        ▼
VoxInputApp.toggle_listening()
```

### 9.2 Why SIGUSR1 Instead of pynput?

The original design used `pynput.GlobalHotKeys`. This was abandoned due to:
1. **Double-triggering**: Both the GNOME keybinding and pynput intercepted the key simultaneously
2. **Linux X11 reliability**: pynput's global hotkey capture on Wayland/X11 is inconsistent
3. **Thread complexity**: pynput hotkey listener on a daemon thread can interfere with GTK's event loop

SIGUSR1 is clean, reliable, and OS-native. The toggle.sh approach also enables launching the app from the hotkey if it isn't running.

### 9.3 SIGINT Handler

```python
signal.signal(signal.SIGINT, lambda s, f: self.quit_app())
```

Ctrl+C triggers graceful shutdown: stop listening → terminate audio → Gtk.main_quit() → sys.exit(0).

---

## 10. Testing Infrastructure

### 10.1 Test Framework

| Tool | Role |
|------|------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (`--asyncio-mode=auto`) |
| `unittest.mock` | Hardware mocking (pyaudio, vosk, gi) |
| `ruff` | Linting (`E`, `F`, `B`, `I` rules) |
| `mypy` | Type checking (`--ignore-missing-imports`) |

### 10.2 Mock Strategy (`conftest.py`)

Hardware dependencies are mocked at the module level **before any imports**:

```python
sys.modules["pyaudio"] = MagicMock()
sys.modules["vosk"] = MagicMock()
sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()
sys.modules["gi.repository.Gtk"] = MagicMock()
sys.modules["gi.repository.GLib"] = MagicMock()
```

This allows all `src` modules to import without hardware or display server present (CI-safe).

### 10.3 testing_suite.py

A unified test runner that chains:
1. **Ruff** (linting) — fails fast on lint errors
2. **mypy** (type checking) — targets `src/` only
3. **pytest** — all tests in `tests/`

This acts as a poor-man's CI pipeline for local development.

### 10.4 Test Coverage Assessment

| Layer | Status | Notes |
|-------|--------|-------|
| Unit | ⚠️ Stub dirs exist | No unit test files found in `tests/unit/` |
| Integration | ⚠️ Partial | `test_audio_setup.py` exists (audio device detection) |
| E2E | ⚠️ Stub dir | No E2E test files found in `tests/e2e/` |
| Static Analysis | ✅ Configured | ruff + mypy via pyproject.toml |

**Critical Gap**: No unit tests for `SpeechRecognizer`, `TextInjector`, `SettingsManager`, or `VoxInputApp`.

---

## 11. Deployment & Packaging

### 11.1 install.sh Breakdown

| Step | Action |
|------|--------|
| 0 | Kill existing instances (`pkill -f run.py`) |
| 1 | `apt install` system dependencies |
| 2 | Create Python venv (`--system-site-packages` for GObject access) |
| 3 | `pip install -r requirements.txt` |
| 4 | Download Vosk small model if `model/` doesn't exist |
| 5 | Create `voxinput.desktop` and install to `~/.local/share/applications` |
| 6 | Register GNOME custom keybinding via `gsettings` |
| 7 | Restart `gsd-media-keys` daemon |

**`--system-site-packages` flag**: Required because `python3-gi` (GObject Introspection) cannot be pip-installed — it's a system package. This allows the venv to access the system `gi` module.

### 11.2 PyTorch / CUDA Version

`requirements.txt` pins:
```
torch==2.7.1+cu118
torchvision==0.22.1+cu118
torchaudio==2.7.1+cu118
```
CUDA 11.8 was chosen for compatibility with older NVIDIA GPUs (Maxwell, Pascal architectures). For newer cards (Ampere+), CUDA 12.x would be more appropriate.

**5.4GB memory footprint**: Loading a Whisper model (especially `small`+) plus PyTorch occupies significant RAM. Documented as a concern on 32GB shared systems with other ML workloads.

### 11.3 Release Packaging

`bin/create_package.sh` creates `VoxInput_v1.0.zip` — a portable archive that can be deployed on any Ubuntu 24.04+ system with `./install.sh`.

---

## 12. Code Review Findings

### 12.1 Critical Issues

#### [CR-001] `audioop` Module Deprecated
**Severity**: 🔴 High  
**File**: `src/main.py:1`, `src/ui.py:467`  
**Issue**: `audioop` was deprecated in Python 3.11 and **removed in Python 3.13**. `pyproject.toml` targets `>=3.10`, which technically allows installation on Python 3.13 where this will cause an `ImportError`.  
**Fix**: Replace with `numpy`:
```python
# Old:
rms = audioop.rms(data, 2)
# New:
audio_np = np.frombuffer(data, dtype=np.int16)
rms = int(np.sqrt(np.mean(audio_np.astype(np.float64)**2)))
```

#### [CR-002] Singleton SettingsManager Not Thread-Safe in Tests
**Severity**: 🔴 High  
**File**: `src/settings.py:11-18`  
**Issue**: The singleton `_instance` persists across test cases. If `test_A` mutates settings and `test_B` expects clean defaults, results are non-deterministic.  
**Fix**: Add a `reset()` classmethod for test cleanup, and call it in `conftest.py` teardown.

#### [CR-003] Unbounded Audio Queue
**Severity**: 🟠 Medium  
**File**: `src/audio.py:14`  
**Issue**: `queue.Queue()` with no `maxsize`. If Whisper inference is slow (CPU mode), the queue fills with stale audio data. This means text may be injected significantly after it was spoken.  
**Fix**: `queue.Queue(maxsize=50)` with `queue.put_nowait()` and drop-on-full behavior:
```python
try:
    self.queue.put_nowait(in_data)
except queue.Full:
    pass  # Drop stale audio — latency is more important than completeness
```

### 12.2 Medium Issues

#### [CR-004] Dead Code — HOTKEY Constant & _listen_hotkeys Method
**Severity**: 🟡 Low  
**File**: `src/config.py:13`, `src/main.py:167-178`  
**Issue**: `HOTKEY` and `_listen_hotkeys` are unused. The pynput hotkey path is commented out.  
**Fix**: Delete dead code or document clearly as "future feature / experimental".

#### [CR-005] SettingsManager.get() Inconsistent Default for whisper_model_size
**Severity**: 🟡 Low  
**File**: `src/settings.py:40-42`  
**Issue**: `get("whisper_model_size")` has a hardcoded default of `"small"` inside the method body, bypassing the standard `default` parameter. This is surprising and inconsistent.  
**Fix**: Move the default to the call site in `recognizer.py`.

#### [CR-006] Whisper Divergence Not Handled
**Severity**: 🟠 Medium  
**File**: `src/recognizer.py:209-218`  
**Issue**: When Whisper rewrites a word it previously output (e.g., "Recall" → "We call"), the divergence is silently accepted. The user sees incorrect text that cannot be automatically corrected.  
**Fix** (complex): Implement a word-level diff and emit backspaces via `TextInjector.backspace()` to correct the most recent injected word. This is non-trivial and was intentionally deferred; should be a tracked issue.

#### [CR-007] Processing Thread Join Timeout Too Short
**Severity**: 🟡 Low  
**File**: `src/main.py:98`  
**Issue**: `self.processing_thread.join(timeout=1.0)`. If Whisper inference is in progress (can take several seconds on CPU), this timeout will expire and the thread will be abandoned (not actually stopped). This is a graceful shutdown race condition.  
**Fix**: Increase timeout or use an `Event` to signal the thread to exit cleanly.

#### [CR-008] pyproject.toml Missing runtime dependencies
**Severity**: 🟡 Low  
**File**: `pyproject.toml`  
**Issue**: `[project.dependencies]` is not defined in `pyproject.toml`. Dependencies only live in `requirements.txt`. This makes the project incompatible with PEP 517/518 build systems.

### 12.3 Minor Issues

#### [CR-009] Log File Grows Unboundedly
**Severity**: 🟢 Info  
**File**: `src/config.py:16`, `install.sh`  
**Issue**: `voxinput.log` is currently 15.8 MB and grows without rotation. Using `logging.FileHandler` without `RotatingFileHandler`.  
**Fix**: Replace with `logging.handlers.RotatingFileHandler(maxBytes=5MB, backupCount=3)`.

#### [CR-010] GTK3 StatusIcon Deprecated
**Severity**: 🟢 Info  
**File**: `src/ui.py:24`  
**Issue**: `Gtk.StatusIcon` is deprecated since GTK 3.14 and removed in GTK 4. Works fine on GTK3 Ubuntu 24.04 desktops, but will require migration to `libayatana-appindicator` or `libnotify` for long-term compatibility.

#### [CR-011] Hardcoded English Language in Whisper
**Severity**: 🟢 Info  
**File**: `src/recognizer.py:175`  
**Issue**: `language='en'` is hardcoded in the `transcribe()` call. Multi-language users cannot use Whisper's language detection.  
**Fix**: Expose `language` as a setting option.

---

## 13. Known Limitations & Technical Debt

| # | Limitation | Workaround | Fix Complexity |
|---|------------|------------|----------------|
| L-01 | Whisper word divergence corrupts injected text | Use Vosk engine | High |
| L-02 | Whisper memory: 5.4GB footprint on CPU+GPU | Use Vosk for low-RAM systems | N/A (model size) |
| L-03 | X11 only — no Wayland native support | Run under XWayland (usually works) | High |
| L-04 | GNOME only for hotkey installation | Manual shortcut setup on KDE/i3 | Medium |
| L-05 | No word deletion/correction capability | Manually delete after dictation | High |
| L-06 | `audioop` will break on Python 3.13+ | Pin to Python ≤3.12 | Medium |
| L-07 | Log file grows without bound | Manually delete voxinput.log | Low |
| L-08 | No multi-language Whisper support | None | Low |
| L-09 | Vosk: no punctuation in output | Use Whisper for punctuated output | N/A (model) |
| L-10 | Test suite: 2 of 3 tiers empty (unit, e2e) | Manual testing | Medium |

---

## 14. Roadmap Recommendations

### Phase 1 — Stability & Correctness (Near-term)

- [ ] **[P1-01]** Replace `audioop` with `numpy` (fix CR-001) — Python 3.13 compatibility
- [ ] **[P1-02]** Cap audio queue to 50 frames (fix CR-003) — prevent stale audio injection
- [ ] **[P1-03]** Add `RotatingFileHandler` (fix CR-009) — prevent 100MB+ log files
- [ ] **[P1-04]** Fix `SettingsManager` singleton test pollution (fix CR-002)
- [ ] **[P1-05]** Increase thread join timeout to 5s or implement Event-based shutdown (fix CR-007)

### Phase 2 — Quality & Testing (Medium-term)

- [ ] **[P2-01]** Write unit tests for `SpeechRecognizer` (mock whisper/vosk)
- [ ] **[P2-02]** Write unit tests for `TextInjector` (mock subprocess)
- [ ] **[P2-03]** Write unit tests for `SettingsManager` (tmp_path fixture)
- [ ] **[P2-04]** Write E2E smoke test (process launch, SIGUSR1, graceful shutdown)
- [ ] **[P2-05]** Remove dead code: `HOTKEY`, `_listen_hotkeys` (fix CR-004)

### Phase 3 — Feature Enhancement (Long-term)

- [ ] **[P3-01]** Whisper word divergence correction using `backspace()` injection
- [ ] **[P3-02]** Multi-language support (expose `language` setting for Whisper)
- [ ] **[P3-03]** Wayland support via `ydotool` (replaces `xdotool` for Wayland sessions)
- [ ] **[P3-04]** KDE/i3/other DE hotkey support instructions
- [ ] **[P3-05]** Migrate from `Gtk.StatusIcon` to `libayatana-appindicator3` for GTK4 readiness
- [ ] **[P3-06]** PipeWire-native audio API (replace `pactl` subprocess calls with `pw-cli` or Python bindings)
- [ ] **[P3-07]** Punctuation post-processing for Vosk output (e.g., voice commands: "period", "comma")
- [ ] **[P3-08]** `pyproject.toml` runtime dependencies (`[project.dependencies]`) for PEP 517 compliance

---

## Appendix A: Dependency Matrix

| Package | Version | Role | Required By |
|---------|---------|------|-------------|
| `vosk` | >=0.3.45 | Offline ASR (Kaldi) | Vosk engine |
| `pyaudio` | >=0.2.14 | Audio capture | AudioCapture |
| `pynput` | >=1.7.7 | Keyboard simulation fallback | TextInjector |
| `openai-whisper` | latest | Batch STT | Whisper engine |
| `numpy` | latest | Audio array operations | Whisper engine |
| `torch` | 2.7.1+cu118 | PyTorch runtime | Whisper inference |
| `torchvision` | 0.22.1+cu118 | Vision ops (Whisper dep) | openai-whisper |
| `torchaudio` | 2.7.1+cu118 | Audio ops | openai-whisper |
| `python3-gi` | system | GTK GObject Introspection | SystemTrayApp |
| `gir1.2-gtk-3.0` | system | GTK3 bindings | SystemTrayApp |
| `xdotool` | system | X11 keyboard simulation | TextInjector (primary) |
| `ffmpeg` | system | Audio format support | openai-whisper |
| `portaudio19-dev` | system | PortAudio backend | PyAudio |

## Appendix B: Key File Reference

| File | Purpose | Owner |
|------|---------|-------|
| `src/main.py` | App orchestrator, signal handlers, main loop | Core |
| `src/recognizer.py` | Dual-engine STT, lag stabilization algorithms | Core |
| `src/audio.py` | PyAudio stream manager, callback queue | Core |
| `src/injection.py` | xdotool/pynput text injection | Core |
| `src/ui.py` | GTK3 system tray + full settings dialog | UI |
| `src/pulseaudio_helper.py` | PulseAudio device enumeration via pactl | Audio |
| `src/config.py` | Compile-time constants | Config |
| `src/settings.py` | Singleton JSON settings manager | Config |
| `install.sh` | Full system installer (apt + pip + gsettings) | Ops |
| `bin/toggle.sh` | Hotkey entry: launch or SIGUSR1 | Ops |
| `bin/create_package.sh` | Release zip builder | Ops |
| `tests/conftest.py` | Hardware mock setup | Testing |
| `testing_suite.py` | Unified local CI: ruff + mypy + pytest | Testing |

---

*PHANTOM.md — VoxInput Phantom Signal Specification — v1.0.0*  
*Built for the Linux community. 100% offline. 100% yours.*
