# VX-FED-001 — VoxInput Feature Enhancement Document
## *Phantom Signal: Evolution Roadmap*

> **Document ID**: VX-FED-001  
> **Version**: 1.0.0  
> **Status**: Active  
> **Date**: 2026-02-20  
> **Feeds From**: PHANTOM.md (Code Review Sections 12–14)  
> **Project**: [VoxInput](https://github.com/bdavidriggins/VoxInput)

---

## Executive Summary

This document defines a **gated, phase-locked feature enhancement plan** for VoxInput. Each gate requires that all tests in the prior phase pass before work on the next phase begins. The three primary focus areas are:

1. **🔴 Stability** — Fix critical bugs from the code review before any enhancements
2. **⚡ Speed** — Achieve sub-100ms perceived word-to-screen latency using SOTA techniques
3. **🔤 Intelligence** — Add real-time spell correction and post-processing powered by SymSpellPy

---

## Competitive Landscape

Before defining enhancements, the following similar open-source projects were analyzed to identify SOTA approaches:

| Project | Engine | Key Innovation | Latency |
|---------|--------|----------------|---------|
| **nerd-dictation** (ideasman42) | Vosk | Hackable single script, Wayland via ydotool | ~200ms |
| **Numen** | Vosk | Voice control + dictation, hands-free design | ~200ms |
| **Talon Voice** | Conformer D (proprietary) | Programmable voice workflows, eye tracking | ~80ms |
| **WhisperLive** (collabora) | faster-whisper + TensorRT | Client-server streaming with speaker diarization | ~300ms |
| **WhisperLiveKit** (SOTA 2025) | faster-whisper + AlignAtt | Simultaneous speech policy, SOTA streaming | ~150ms |
| **nerd-dictation** Whisper fork | faster-whisper | CTranslate2 INT8 quantization | ~400ms CPU |
| **whisper.cpp** | GGML C++ | CPU-native, no Python overhead, Metal/CUDA | ~50ms |
| **VoxInput (current)** | Vosk / openai-whisper | Lag-N stabilization, PyAudio queue | ~200ms Vosk / ~800ms Whisper CPU |

### Key SOTA Insights

1. **`faster-whisper` (CTranslate2)** is the single biggest Whisper upgrade: 4x faster inference, 50% less VRAM, supports INT8/FP16 quantization. Drop-in replacement for `openai-whisper`.
2. **Chunk size reduction** for Vosk: Current 8000-frame chunks = 500ms of audio. Optimal is 100–200ms (1600–3200 frames). Cutting chunk size alone halves perceived latency.
3. **SymSpellPy** can correct 1M+ words/second with O(1) lookup — negligible overhead inserted after each injected word batch.
4. **`ydotool`** (Wayland-native) as a sibling to `xdotool` enables Wayland session support, which Talon Voice and nerd-dictation already exploit.
5. **Whisper Large-V3-Turbo** achieves 6x speed over Large-V3 at near-identical accuracy — significant quality upgrade path with no architecture changes needed.

---

## Gate Definitions

Each gate is a mandatory checkpoint. Work on the next phase does NOT begin unless:
- All new unit/integration tests pass (`pytest` exit 0)
- Ruff linting passes (`ruff check .` exit 0)
- MyPy passes (`mypy src/` exit 0)
- A manual smoke test is run and documented

```
GATE-0 ──► GATE-1 ──► GATE-2 ──► GATE-3 ──► GATE-4
[Infra]    [Speed]    [Engine]   [Spellcheck] [Polish]
```

---

## Phase 0: Foundation (Pre-Gate) — Bug Fixes from Code Review

> **Goal**: Make VoxInput correct and stable before adding any new features.  
> **Risk if skipped**: New features will be built on broken foundations.  
> **Estimated effort**: 2–4 hours

### P0-01 — Replace `audioop` with NumPy RMS
**From**: CR-001 (Python 3.13 compatibility)  
**Files**: `src/main.py`, `src/ui.py`

```diff
# src/main.py - imports
-import audioop
+import numpy as np

# In _process_loop:
-rms = audioop.rms(data, 2)
+audio_np = np.frombuffer(data, dtype=np.int16)
+rms = int(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))

# src/ui.py - In _update_level():
-import audioop
-rms = audioop.rms(data, 2)
+audio_np = np.frombuffer(data, dtype=np.int16)
+rms = int(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
```

### P0-02 — Cap Audio Queue to Prevent Stale Audio
**From**: CR-003 (unbounded queue)  
**Files**: `src/audio.py`

```diff
-self.queue = queue.Queue()
+self.queue = queue.Queue(maxsize=50)  # ~25 seconds of audio max

# In _callback:
-self.queue.put(in_data)
+try:
+    self.queue.put_nowait(in_data)
+except queue.Full:
+    pass  # Drop oldest chunk; freshness > completeness
```

### P0-03 — Add Rotating Log Handler
**From**: CR-009 (log file is 15.8MB, will grow forever)  
**Files**: `src/main.py`

```diff
+from logging.handlers import RotatingFileHandler

 handlers=[
-    logging.FileHandler(LOG_FILE),
+    RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3),
     logging.StreamHandler(sys.stdout)
 ]
```

### P0-04 — Fix Thread Shutdown Timeout
**From**: CR-007  
**Files**: `src/main.py`

```diff
-self.processing_thread.join(timeout=1.0)
+self.processing_thread.join(timeout=8.0)  # Must outlast worst-case Whisper CPU inference
```

### P0-05 — Fix SettingsManager Singleton Test Pollution
**From**: CR-002  
**Files**: `src/settings.py`, `tests/conftest.py`

Add to `SettingsManager`:
```python
@classmethod
def reset(cls):
    """Reset singleton for test isolation."""
    cls._instance = None
```

Add to `conftest.py`:
```python
@pytest.fixture(autouse=True)
def reset_settings():
    from src.settings import SettingsManager
    SettingsManager.reset()
    yield
    SettingsManager.reset()
```

### 🚦 GATE-0 Tests

```bash
# Required to pass before Phase 1:
pytest tests/ -v
ruff check .
mypy src/
python3 -c "import src.main"  # Verify no audioop import errors

# Manual smoke test:
python3 run.py  # App starts, tray icon appears, hotkey works
```

---

## Phase 1: Speed — Vosk Latency Reduction ⚡

> **Goal**: Make the Vosk engine feel instantaneous. Words appear within 50–100ms of being spoken.  
> **SOTA Basis**: Alphacephei docs recommend 100-200ms chunks for real-time feel.  
> **Estimated effort**: 3–5 hours

### P1-01 — Reduce Audio Chunk Size (500ms → 100ms)

This is the **single highest impact change** for perceived Vosk latency. The current `CHUNK_SIZE = 8000` causes 500ms of audio to accumulate before processing. Reducing to 1600 frames = 100ms per cycle.

**Files**: `src/config.py`

```diff
-CHUNK_SIZE = 8000  # 500ms @ 16kHz
+CHUNK_SIZE = 1600  # 100ms @ 16kHz — optimal for real-time feel
```

> **⚠️ Warning**: Smaller chunks increase CPU call frequency. Benchmark on target hardware. If CPU spikes, use `CHUNK_SIZE = 3200` (200ms) as a compromise.

### P1-02 — Vosk: Lower Stability Lag to 0 for Full Result

When Vosk fires a full result (sentence-end), there is no reason to hold back any words. Add an explicit check:

**Files**: `src/recognizer.py` — `_process_vosk()`

```diff
# Full Result path
 if self.recognizer.AcceptWaveform(data):
     result = json.loads(self.recognizer.Result())
     text = result.get('text', '')
     words = text.split()
-    if len(words) > len(self.committed_text):
-        new_words_to_inject = words[len(self.committed_text):]
+    # Full result = final. Inject ALL uncommitted words with zero lag.
+    new_words_to_inject = words[len(self.committed_text):]
     self.committed_text = []
```

### P1-03 — Inject Partial Words Immediately (LAG=0 for fast typing mode)

Add a `fast_mode` setting that sets `stability_lag = 0` — for users who prefer speed over correction stability.

**Files**: `src/settings.py`, `src/recognizer.py`, `src/ui.py`

Add to settings dialog a "Speed Mode" toggle checkbox:
```python
# In SettingsDialog, Advanced Options section:
self.check_fast_mode = Gtk.CheckButton(label="⚡ Speed Mode (LAG=0, fastest output)")
self.check_fast_mode.set_active(self.temp_settings.get("fast_mode", False))
self.check_fast_mode.connect("toggled", lambda w: self._set_temp("fast_mode", w.get_active()))
```

In `_process_vosk` and `_process_whisper`:
```python
LAG = 0 if self.settings.get("fast_mode", False) else self.settings.get("stability_lag", 1)
```

### P1-04 — Move Text Injection to a Dedicated Thread

`xdotool` is a subprocess call with measurable latency (~15–40ms). Currently this blocks the processing loop, preventing new audio from being processed until injection completes.

**Files**: `src/main.py`, `src/injection.py`

```python
# In VoxInputApp.__init__:
import queue as q
self.injection_queue = q.Queue(maxsize=100)
self.injection_thread = threading.Thread(target=self._injection_loop, daemon=True)
self.injection_thread.start()

def _injection_loop(self):
    while not self.should_quit:
        try:
            text = self.injection_queue.get(timeout=0.1)
            self.injector.type_text(text)
        except q.Empty:
            continue

# In _process_loop, replace direct injection calls:
# OLD: self.injector.type_text(text)
# NEW:
try:
    self.injection_queue.put_nowait(text)
except q.Full:
    logger.warning("Injection queue full, dropping word batch")
```

### 🚦 GATE-1 Tests

```bash
pytest tests/ -v  # All P0 + P1 tests pass

# Latency Benchmark (manual):
# 1. Start VoxInput with Vosk engine
# 2. Speak a single word ("hello")
# 3. Time from speech onset to character appearing on screen
# TARGET: < 150ms end-to-end
```

**New unit tests to write** (`tests/unit/test_audio.py`):
- `test_queue_drops_on_full()` — verify audio is dropped gracefully
- `test_chunk_size_is_100ms()` — verify CHUNK_SIZE=1600
- `test_processing_thread_decoupled_from_injection()` — verify injection runs separately

---

## Phase 2: Engine Upgrade — `faster-whisper` Integration 🚀

> **Goal**: Replace `openai-whisper` with `faster-whisper` (CTranslate2). 4x speed increase for Whisper engine. Enable Whisper Large-V3-Turbo as a new model option.  
> **SOTA Basis**: `faster-whisper` benchmarks: 13 min audio in 11.47s (batched). CPU latency reduced from ~800ms to ~200ms per chunk.  
> **Estimated effort**: 4–6 hours

### P2-01 — Add `faster-whisper` as Optional Backend

Install:
```bash
pip install faster-whisper
```

Add to `requirements.txt`:
```
faster-whisper>=1.0.3
```

> **Note**: Keep `openai-whisper` as a fallback. `faster-whisper` is a drop-in replacement but has slightly different API.

### P2-02 — Refactor Whisper Model Loading in `recognizer.py`

```python
# In SpeechRecognizer.__init__, Whisper branch:
use_faster_whisper = self.settings.get("use_faster_whisper", True)

if use_faster_whisper:
    try:
        from faster_whisper import WhisperModel
        compute_type = "int8"  # Maximum speed on CPU
        device = "cuda" if torch_available else "cpu"
        self.model = WhisperModel(size, device=device, compute_type=compute_type)
        self.whisper_backend = "faster"
        logger.info(f"faster-whisper loaded: {size} on {device} with {compute_type}")
    except ImportError:
        logger.warning("faster-whisper not installed, falling back to openai-whisper")
        use_faster_whisper = False

if not use_faster_whisper:
    # Original openai-whisper path
    self.model = whisper.load_model(size)
    self.whisper_backend = "openai"
```

### P2-03 — Update `_process_whisper` for `faster-whisper` API

`faster-whisper` returns a generator of segments, not a dict:

```python
def _process_whisper(self, data):
    ...
    if self.whisper_backend == "faster":
        segments, info = self.model.transcribe(
            audio_np,
            beam_size=1,
            language="en",
            vad_filter=True,         # Built-in VAD — skip silent segments
            vad_parameters=dict(min_silence_duration_ms=200)
        )
        current_transcript = " ".join(s.text.strip() for s in segments)
    else:
        # Legacy openai-whisper path
        result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language='en')
        current_transcript = result.get('text', '').strip()
```

### P2-04 — Add Large-V3-Turbo Model Option

Expand the model size options in `ui.py` SettingsDialog:

```diff
-for size in ["tiny", "base", "small", "medium", "large"]:
+for size in ["tiny", "base", "small", "medium", "large", "large-v3-turbo", "distil-large-v3"]:
     self.combo_whisper.append_text(size)
```

> **large-v3-turbo**: 6x faster than large-v3, near-identical accuracy. Best for users with GPU.  
> **distil-large-v3**: 6x faster than large-v3, slightly reduced accuracy. Best CPU option.

### P2-05 — Enable Built-in VAD (Voice Activity Detection)

`faster-whisper` ships with Silero VAD integration. This means Whisper can **self-detect silence** and only transcribe speech segments — eliminating the need for the manual `audioop.rms` silence detection loop for the Whisper path.

```python
# In recognizer.py, _process_whisper (faster-whisper):
segments, info = self.model.transcribe(
    audio_np,
    language="en",
    beam_size=1,
    vad_filter=True,
    vad_parameters=dict(
        threshold=0.5,
        min_silence_duration_ms=int(self.settings.get("silence_duration", 0.6) * 1000)
    )
)
```

When VAD is enabled, the main loop's RMS silence detection for Whisper becomes redundant (but harmless). Log a note.

### P2-06 — Reduce Whisper Buffer Minimum from 1s to 0.5s

```diff
-if len(self.whisper_buffer) < SAMPLE_RATE * 2 * 1.0:
+if len(self.whisper_buffer) < SAMPLE_RATE * 2 * 0.5:  # 0.5s minimum
     return None
```

With faster inference (faster-whisper + INT8), processing at 0.5s intervals is viable without CPU overload.

### 🚦 GATE-2 Tests

```bash
pip install faster-whisper
pytest tests/ -v

# Whisper Benchmark test (manual):
# 1. Switch to Whisper engine in settings
# 2. Speak a sentence: "The quick brown fox jumps over the lazy dog"
# 3. All words should appear within 1 second of sentence end
# TARGET: < 1000ms Whisper end-to-end on CPU (< 300ms on GPU)

# Regression test:
# 1. Switch back to Vosk — verify Vosk still works correctly
# 2. Confirm no import errors if faster-whisper not installed
```

**New integration tests** (`tests/integration/test_whisper_engine.py`):
- `test_faster_whisper_loads_gracefully()` — verify import + model load doesn't crash
- `test_openai_whisper_fallback()` — mock faster-whisper ImportError, verify fallback
- `test_vad_filter_skips_silence()` — verify silent buffer returns None
- `test_large_v3_turbo_in_settings()` — verify model size appears in settings dialog

---

## Phase 3: Real-Time Spell Correction 🔤

> **Goal**: Transparently correct speech recognition errors (homophones, ASR artifacts) before text reaches the cursor. Sub-millisecond per-word overhead.  
> **SOTA Basis**: SymSpellPy corrects 1M+ words/second using pre-computed lookup tables.  
> **Estimated effort**: 5–8 hours

### P3-01 — Architecture Decision: Where to Spell Check

```
Option A: Post-injection correction (complex — requires backspace simulation)
Option B: Pre-injection correction (simple — correct before xdotool call)  ← CHOSEN
```

**Pre-injection** is the right approach: we intercept text in `TextInjector.type_text()` before it's sent to xdotool. The user never sees the uncorrected text.

```
Audio → Recognizer → [NEW: SpellCorrector.correct(text)] → TextInjector
```

### P3-02 — New Module: `src/spell_corrector.py`

```python
"""
SpellCorrector — Real-time ASR output correction using SymSpellPy.
Corrects only out-of-vocabulary words. Preserves proper nouns and
user-defined custom terms. Sub-millisecond per-word overhead.
"""
import logging
from symspellpy import SymSpell, Verbosity

logger = logging.getLogger(__name__)

# Word frequency dictionary (English 82,765 words)
DICT_PATH = "assets/frequency_dictionary_en_82_765.txt"

class SpellCorrector:
    """
    Real-time spell correction for ASR output.
    - Uses SymSpellPy for O(1) lookup
    - Only corrects words not found in dictionary (OOV words)
    - Preserves user custom words (user dictionary)
    - Thread-safe: SymSpell is read-only after initialization
    """

    def __init__(self, settings):
        self.settings = settings
        self.enabled = settings.get("spell_check_enabled", True)
        self.sym_spell = None
        self._load()

    def _load(self):
        if not self.enabled:
            return
        try:
            self.sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
            self.sym_spell.load_dictionary(DICT_PATH, term_index=0, count_index=1)

            # Load custom user dictionary if exists
            user_dict = self.settings.get("custom_dict_path")
            if user_dict:
                self.sym_spell.load_dictionary(user_dict, term_index=0, count_index=1)

            logger.info("SpellCorrector initialized with SymSpellPy")
        except Exception as e:
            logger.error(f"SpellCorrector failed to initialize: {e}")
            self.sym_spell = None

    def correct(self, text: str) -> str:
        """
        Correct a batch of words. Returns corrected text.
        Called on every word batch before injection.
        """
        if not self.enabled or self.sym_spell is None:
            return text

        words = text.split()
        corrected = []
        for word in words:
            # Preserve capitalized words (proper nouns, acronyms)
            if word[0].isupper() or word.isupper():
                corrected.append(word)
                continue

            suggestions = self.sym_spell.lookup(
                word.lower(), Verbosity.CLOSEST, max_edit_distance=2
            )
            if suggestions and suggestions[0].term != word.lower():
                fix = suggestions[0].term
                logger.debug(f"SpellCorrector: '{word}' → '{fix}'")
                corrected.append(fix)
            else:
                corrected.append(word)

        return " ".join(corrected)
```

### P3-03 — Integrate SpellCorrector into VoxInputApp

**Files**: `src/main.py`

```python
# In __init__:
from .spell_corrector import SpellCorrector
self.spell = SpellCorrector(self.settings)

# In _process_loop, before injection:
# OLD:
if text:
    self.injector.type_text(text)

# NEW:
if text:
    corrected = self.spell.correct(text)
    self.injector.type_text(corrected)
```

### P3-04 — Download SymSpell Dictionary in `install.sh`

```bash
# In install.sh, after model download:
DICT_FILE="assets/frequency_dictionary_en_82_765.txt"
if [ ! -f "$DICT_FILE" ]; then
    echo "Downloading SymSpell English dictionary..."
    wget -q "https://raw.githubusercontent.com/mammothb/symspellpy/master/symspellpy/frequency_dictionary_en_82_765.txt" \
         -O "$DICT_FILE"
    echo "Dictionary installed."
fi
```

Add to `requirements.txt`:
```
symspellpy>=6.7.7
```

### P3-05 — Settings UI: Spell Check Toggle

Add to SettingsDialog Advanced Options:

```python
# Spell Check Toggle
self.check_spell = Gtk.CheckButton(label="✓ Real-time spell correction (SymSpellPy)")
self.check_spell.set_active(self.temp_settings.get("spell_check_enabled", True))
self.check_spell.connect("toggled", lambda w: self._set_temp("spell_check_enabled", w.get_active()))
grid_adv.attach(self.check_spell, 0, 8, 2, 1)

# Custom dictionary path
lbl_dict = Gtk.Label(label="Custom Word List:")
lbl_dict.set_halign(Gtk.Align.START)
grid_adv.attach(lbl_dict, 0, 9, 1, 1)

self.file_dict = Gtk.FileChooserButton(title="Custom Dictionary", action=Gtk.FileChooserAction.OPEN)
self.file_dict.connect("file-set", lambda w: self._set_temp("custom_dict_path", w.get_filename()))
grid_adv.attach(self.file_dict, 1, 9, 1, 1)
```

### P3-06 — ASR-Specific Correction Rules (Post-Processing Pipeline)

Beyond dictionary lookup, common ASR errors follow patterns. Add a lightweight rule engine:

**Files**: `src/spell_corrector.py`

```python
# Common ASR artifacts for English dictation
ASR_CORRECTIONS = {
    # Vosk artifacts (no punctuation fallout)
    "gonna": "going to",
    "wanna": "want to",
    "gotta": "got to",
    # Homophone handling (context-free, frequency-based)
    "their": "their",  # Keep as-is; context needed for there/they're
    # Common short words ASR mangles
    "two": "to",  # Will need context awareness to fix properly
}

def _apply_asr_rules(self, text: str) -> str:
    """Apply VoxInput-specific ASR correction rules."""
    words = text.split()
    return " ".join(ASR_CORRECTIONS.get(w.lower(), w) for w in words)
```

> **Note**: Context-dependent corrections (their/there/they're, to/two/too) require a language model for reliable correction and are out of scope for Phase 3. Track as Phase 4 enhancement.

### 🚦 GATE-3 Tests

```bash
pip install symspellpy
pytest tests/ -v

# Spell correction unit tests (tests/unit/test_spell_corrector.py):
# - test_correct_typos() — "teh" → "the", "recieve" → "receive"
# - test_preserves_proper_nouns() — "John" stays "John"
# - test_disabled_passthrough() — when disabled, returns text unchanged
# - test_oov_preserved() — "VoxInput" not mangled
# - test_correction_speed() — 1000 words < 50ms total

# Integration test:
# - test_spell_corrector_in_process_loop() — mock recognizer returns "teh quik", verify "the quick" is injected
```

---

## Phase 4: Polish & Wayland Support 🐧

> **Goal**: Broaden platform support, improve UX, and close the final code quality gaps.  
> **Estimated effort**: 6–10 hours

### P4-01 — Wayland Support via `ydotool`

`xdotool` does not work on native Wayland sessions (only XWayland). Add `ydotool` as a second-priority backend:

**Files**: `src/injection.py`

```python
def type_text(self, text):
    text = text.strip()
    if not text:
        return
    full_text = text + ' '

    # Priority 1: xdotool (X11/XWayland)
    try:
        subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '0', full_text], check=True, timeout=2)
        return
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Priority 2: ydotool (native Wayland)
    try:
        subprocess.run(['ydotool', 'type', '--', full_text], check=True, timeout=2)
        return
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("ydotool failed, falling back to pynput")

    # Priority 3: pynput (universal fallback)
    try:
        self.keyboard.type(full_text)
    except Exception as e:
        logger.error(f"All injection methods failed: {e}")
```

Add to `install.sh`:
```bash
# Optional ydotool for Wayland support
if command -v ydotool > /dev/null 2>&1; then
    echo "✓ ydotool available (Wayland support enabled)"
else
    echo "ℹ Optional: Install ydotool for native Wayland support: sudo apt install ydotool"
fi
```

### P4-02 — Vosk Punctuation Post-Processing (Voice Punctuation Commands)

Vosk outputs only lowercase without punctuation. Add a voice-command punctuation layer:

**Files**: `src/spell_corrector.py` (extend) or new `src/post_processor.py`

```python
VOICE_PUNCTUATION = {
    "period": ".",
    "comma": ",",
    "question mark": "?",
    "exclamation mark": "!",
    "exclamation point": "!",
    "new line": "\n",
    "new paragraph": "\n\n",
    "open paren": "(",
    "close paren": ")",
    "colon": ":",
    "semicolon": ";",
    "dash": "–",
    "ellipsis": "...",
}

def apply_voice_punctuation(text: str) -> str:
    """Replace spoken punctuation with symbols."""
    for phrase, symbol in VOICE_PUNCTUATION.items():
        text = text.replace(phrase, symbol)
    return text
```

### P4-03 — `pyproject.toml` Runtime Dependencies

Add formal PEP 517 dependencies:

```toml
[project.dependencies]
vosk = ">=0.3.45"
pyaudio = ">=0.2.14"
pynput = ">=1.7.7"
numpy = "*"
symspellpy = ">=6.7.7"
# faster-whisper and openai-whisper are optional extras
```

```toml
[project.optional-dependencies]
whisper-fast = ["faster-whisper>=1.0.3"]
whisper-original = ["openai-whisper", "torch", "torchvision", "torchaudio"]
dev = ["ruff", "mypy", "pytest", "pytest-asyncio"]
```

### P4-04 — Migrate from `Gtk.StatusIcon` to `libayatana-appindicator3`

`Gtk.StatusIcon` is deprecated in GTK3 and removed in GTK4. Modern GNOME uses AppIndicator:

```python
# Detect and use best available tray implementation:
try:
    import gi
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    INDICATOR_BACKEND = "ayatana"
except (ImportError, ValueError):
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3
        INDICATOR_BACKEND = "appindicator"
    except (ImportError, ValueError):
        INDICATOR_BACKEND = "statusicon"  # Legacy fallback
```

### P4-05 — Multi-Language Whisper Support

```python
# In SettingsDialog, add language selector for Whisper:
self.combo_language = Gtk.ComboBoxText()
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "auto"]
for lang in SUPPORTED_LANGUAGES:
    self.combo_language.append_text(lang)
```

In `recognizer.py`:
```diff
-result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language='en')
+whisper_lang = self.settings.get("whisper_language", "en")
+lang_arg = None if whisper_lang == "auto" else whisper_lang
+result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language=lang_arg)
```

### 🚦 GATE-4 Tests

```bash
pytest tests/ -v

# Platform tests (manual):
# X11 session: verify xdotool path
# XWayland session: verify xdotool still works
# Pure Wayland (if available): verify ydotool path

# Voice punctuation test:
# Speak: "Hello comma how are you period"
# Expected inject: "Hello, how are you."
```

---

## New Dependency Summary

| Dependency | Phase | PyPI Package | Purpose |
|------------|-------|-------------|---------|
| `symspellpy` | P3 | `symspellpy>=6.7.7` | Real-time spell correction |
| `faster-whisper` | P2 | `faster-whisper>=1.0.3` | 4x faster Whisper inference |
| `ydotool` | P4 | system (`apt install ydotool`) | Wayland text injection |

---

## Test Coverage Plan

### New Test Files to Create

```
tests/
├── unit/
│   ├── test_audio.py           # AudioCapture queue behavior
│   ├── test_settings.py        # SettingsManager singleton, load/save
│   ├── test_injection.py       # TextInjector mock xdotool/fallback
│   ├── test_spell_corrector.py # SymSpellPy correction logic
│   └── test_recognizer.py      # Vosk/Whisper processing logic (mocked models)
├── integration/
│   ├── test_audio_setup.py     # (existing) 
│   ├── test_whisper_engine.py  # faster-whisper integration
│   └── test_full_pipeline.py   # Audio → Recognizer → Spell → Inject (all mocked)
└── e2e/
    └── test_app_lifecycle.py   # App start → toggle → text appears → quit
```

### Test Coverage Targets

| Module | Current | Target |
|--------|---------|--------|
| `recognizer.py` | 0% | 80% |
| `audio.py` | 0% | 70% |
| `injection.py` | 0% | 80% |
| `settings.py` | 0% | 90% |
| `spell_corrector.py` | N/A (new) | 85% |
| `main.py` | 0% | 50% |

---

## Performance Benchmark Targets

| Metric | Current | Phase 1 Target | Phase 2 Target |
|--------|---------|----------------|----------------|
| Vosk: word-to-screen latency | ~400ms | **< 120ms** | ~100ms |
| Vosk: CPU usage (idle listening) | ~5% | ~8% | ~8% |
| Whisper CPU: total utterance latency | ~1500ms | ~1200ms | **< 500ms** |
| Whisper GPU: total utterance latency | ~400ms | ~300ms | **< 150ms** |
| Spell check overhead per word | N/A | N/A | **< 0.1ms** |
| Memory: Vosk only | ~300MB | ~300MB | ~300MB |
| Memory: Whisper base | ~5.4GB | ~5.4GB | **~2.0GB** (faster-whisper INT8) |

---

## Gated Phase Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 0: Foundation (Bug Fixes)                                │
│  P0-01 audioop → numpy  |  P0-02 queue cap  |  P0-03 log rotate│
│  P0-04 thread timeout  |  P0-05 singleton fix                   │
│  ───────────────────────────────────────────────────────────    │
│  🚦 GATE-0: pytest pass + ruff + mypy + manual smoke test        │
└─────────────────────────────────────────────────────────────────┘
                        │ GATE-0 CLEARED
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Speed — Vosk ⚡                                       │
│  P1-01 chunk size 500ms→100ms  |  P1-02 full result LAG=0      │
│  P1-03 fast_mode toggle  |  P1-04 injection thread             │
│  ───────────────────────────────────────────────────────────    │
│  🚦 GATE-1: pytest + latency benchmark < 150ms Vosk             │
└─────────────────────────────────────────────────────────────────┘
                        │ GATE-1 CLEARED
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Engine Upgrade — faster-whisper 🚀                    │
│  P2-01 install  |  P2-02 model loading  |  P2-03 API adapter   │
│  P2-04 large-v3-turbo  |  P2-05 built-in VAD  |  P2-06 buffer  │
│  ───────────────────────────────────────────────────────────    │
│  🚦 GATE-2: pytest + Whisper < 1000ms CPU / < 300ms GPU         │
└─────────────────────────────────────────────────────────────────┘
                        │ GATE-2 CLEARED
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: Spell Correction 🔤                                   │
│  P3-01 architecture  |  P3-02 SpellCorrector module             │  
│  P3-03 integration  |  P3-04 install.sh  |  P3-05 settings UI  │
│  P3-06 ASR rules                                                │
│  ───────────────────────────────────────────────────────────    │
│  🚦 GATE-3: pytest + spell unit tests + 1000 words < 50ms       │
└─────────────────────────────────────────────────────────────────┘
                        │ GATE-3 CLEARED
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: Polish 🐧                                             │
│  P4-01 ydotool Wayland  |  P4-02 voice punctuation             │
│  P4-03 pyproject deps  |  P4-04 AppIndicator3 migration        │
│  P4-05 multi-language Whisper                                   │
│  ───────────────────────────────────────────────────────────    │
│  🚦 GATE-4: full test suite + platform matrix smoke test        │
└─────────────────────────────────────────────────────────────────┘
                        │ GATE-4 CLEARED
                        ▼
                  🎉 v2.0.0 Release
```

---

*VX-FED-001 — VoxInput: Phantom Signal Evolution Roadmap — v1.0.0*  
*Built for the Linux community. Speed, accuracy, privacy.*

---

## Phase 5: SOTA GUI — Ubuntu Linux Redesign 🎨

> **Goal**: Replace the deprecated `Gtk.StatusIcon` with a modern GTK4 + libadwaita interface that feels native on Ubuntu 22.04/24.04.
> **Platform**: Ubuntu Linux (GNOME Shell). GTK4 + libadwaita.
> **Estimated effort**: 8–12 hours

### P5-01 — Migrate Tray: `Gtk.StatusIcon` → `libayatana-appindicator3`

```bash
sudo apt install libayatana-appindicator3-1 gir1.2-ayatanaappindicator3-0.1
```

```python
import gi
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import AyatanaAppIndicator3 as AppIndicator3

indicator = AppIndicator3.Indicator.new(
    "voxinput", "audio-input-microphone",
    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
)
indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
indicator.set_menu(menu)
```

### P5-02 — Real-Time Status OSD (On-Screen Display)

Non-intrusive transparent overlay at screen bottom-center showing 🔴 Recording / ✅ Done when listening toggles.

### P5-03 — Settings: `Adw.PreferencesWindow`

Replace hand-rolled `Gtk.Dialog` with modern `Adw.PreferencesWindow` — sectioned, searchable, dark-mode aware.

```python
import gi; gi.require_version('Adw', '1')
from gi.repository import Adw

class VoxInputPreferences(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__()
        self.set_title("VoxInput Settings")
        page = Adw.PreferencesPage(title="Engine", icon_name="media-playback-start-symbolic")
        self.add(page)
        group = Adw.PreferencesGroup(title="Speech Engine")
        page.add(group)
        self.engine_row = Adw.ComboRow(title="Engine")
        self.speed_row = Adw.SwitchRow(title="Speed Mode", subtitle="LAG=0 — instant output")
        group.add(self.engine_row)
        group.add(self.speed_row)
```

### P5-04 — Dark Mode Support

libadwaita `Adw.StyleManager` follows system preference automatically.

### P5-05 — Live Waveform Cairo Widget

Replace static level bar in mic test with scrolling waveform drawn via Cairo `DrawingArea`.

### 🚦 GATE-5 Tests

```bash
sudo apt install libayatana-appindicator3-1 gir1.2-ayatanaappindicator3-0.1 libadwaita-1-dev
pytest tests/ -v
# Manual: app launches with no GTK deprecation warnings, Adw settings renders correctly
```

---

## Phase 6: Ubuntu Microphone Signal Enhancement 🎙️

> **Goal**: PulseAudio/PipeWire controls inside VoxInput — input volume, noise suppression, mic boost, auto-calibrate. No audio engineering knowledge required.
> **Platform**: Ubuntu (PulseAudio/PipeWire via `pactl` + `amixer`).
> **Estimated effort**: 6–8 hours

### P6-01 — Available Ubuntu Controls

| Control | Tool | Effect |
|---------|------|--------|
| Input volume (0–150%) | `pactl set-source-volume` | Software gain |
| Noise suppression | `pactl load-module module-echo-cancel aec_method=webrtc` | WebRTC AEC |
| Hardware mic boost | `amixer sset 'Mic Boost'` | Pre-amp level |
| Auto-calibrate | Record 3s silence → measure floor | Sets threshold |

### P6-02 — New `src/mic_enhancer.py`

```python
class MicEnhancer:
    def set_input_volume(self, percent: int):
        """0–150%. Persisted to settings."""
        subprocess.run(["pactl", "set-source-volume",
                        self.settings.get("audio_device", "@DEFAULT_SOURCE@"),
                        f"{percent}%"], check=True)
        self.settings.set("mic_volume", percent)

    def enable_noise_suppression(self):
        """Load WebRTC AEC via module-echo-cancel."""
        result = subprocess.check_output([
            "pactl", "load-module", "module-echo-cancel",
            "source_name=VoxInputDenoised",
            f"source_master={self.settings.get('audio_device', '')}",
            "aec_method=webrtc"
        ], text=True)
        self._noise_module_id = result.strip()
        self.settings.set("noise_suppression", True)

    def auto_calibrate(self) -> int:
        """Record 3s silence → measure floor → return recommended threshold."""
        import numpy as np
        from src.audio import AudioCapture
        audio = AudioCapture(); audio.start(); samples = []
        deadline = time.time() + 3.0
        while time.time() < deadline:
            data = audio.get_data()
            if data:
                arr = np.frombuffer(data, dtype=np.int16)
                samples.append(float(np.sqrt(np.mean(arr.astype(np.float64)**2))))
        audio.stop()
        floor = float(np.percentile(samples, 95)) if samples else 300
        return int(floor * 1.5)
```

### P6-03 — Microphone Tab in Settings

```
┌─────────────────────────────────────────────────────────────┐
│  🎙️  Microphone Enhancement                                 │
│                                                             │
│  Input Volume    [━━━━━━━━━━━━●────] 85%   [Reset]         │
│  Noise Suppress  ●  ON  (WebRTC AEC)                        │
│  Mic Boost       [━━━●──────────] Level 1  (ALSA)           │
│                                                             │
│  [🎤 Auto-Calibrate Silence Threshold]                      │
│  ↳ Speak nothing for 3s → threshold auto-set                │
└─────────────────────────────────────────────────────────────┘
```

### 🚦 GATE-6 Tests

```bash
pytest tests/ -v  # includes test_mic_enhancer.py

# Manual:
# - Drag volume slider → mic level bar responds live
# - Toggle noise suppress → pactl list modules short | grep echo
# - Auto-calibrate → silence_threshold updates in settings.json
```

---

## Updated Gate Ladder — v1.1.0

```
GATE-0 → GATE-1 → GATE-2 → GATE-3 → GATE-4 → GATE-5 → GATE-6
[P0]     [P1]     [P2]     [P3]     [P4]     [P5]     [P6]
Fixes    Speed    Whisper  Spell    Wayland  SOTA-GUI  Mic+Boost
                                                        → v2.0.0
```

---

*VX-FED-001 — v1.1.0 — Ubuntu Linux. Speed, accuracy, privacy.*
