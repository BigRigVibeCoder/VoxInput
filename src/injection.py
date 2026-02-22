"""
src/injection.py — Text injection engine for VoxInput. (Phase 4 update)

Injection strategy (in priority order):
  1. ydotool  — Wayland-native, works everywhere, no DISPLAY needed (P4-01)
  2. xdotool  — X11, works on XWayland sessions
  3. pynput   — Pure Python fallback, works on X11 only

Voice punctuation commands (P4-02):
  "new line"       → newline character
  "new paragraph"  → double newline
  "period"         → .
  "comma"          → ,
  "question mark"  → ?
  "exclamation"    → !
  "colon"          → :
  "semicolon"      → ;
  "open paren"     → (
  "close paren"    → )
  "open bracket"   → [
  "close bracket"  → ]
  "dash" / "hyphen" → -
  "delete that"    → (handled externally by main.py)
"""
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

# ─── Voice-to-punctuation command map (P4-02) ─────────────────────────────
# Keys must already be lowercase-normalized by the recognizer.
# Longer phrases first to catch "question mark" before "mark".
PUNCT_COMMANDS: list[tuple[str, str]] = [
    ("new paragraph",    "\n\n"),
    ("new line",         "\n"),
    ("open parenthesis", "("),
    ("close parenthesis",")"),
    ("open paren",       "("),
    ("close paren",      ")"),
    ("open bracket",     "["),
    ("close bracket",    "]"),
    ("question mark",    "?"),
    ("exclamation mark", "!"),
    ("exclamation point","!"),
    ("semicolon",        ";"),
    ("colon",            ":"),
    ("comma",            ","),
    ("period",           "."),
    ("full stop",        "."),
    ("hyphen",           "-"),
    ("dash",             "-"),
    ("ellipsis",         "..."),
]

# Build a compiled regex for fast multi-phrase matching
_PUNCT_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(phrase) for phrase, _ in PUNCT_COMMANDS) + r')\b',
    re.IGNORECASE
)
_PUNCT_MAP = {phrase.lower(): sym for phrase, sym in PUNCT_COMMANDS}

# First words of multi-word commands — these need cross-batch buffering
_MULTI_WORD_PREFIXES = set()
for phrase, _ in PUNCT_COMMANDS:
    words = phrase.lower().split()
    if len(words) > 1:
        _MULTI_WORD_PREFIXES.add(words[0])


def apply_voice_punctuation(text: str) -> str:
    """
    Replace voice punctuation command phrases with their symbols.

    'hello period new line' → 'hello.\n'

    Called before injection so the recognizer stays punctuation-agnostic.
    """
    def _replace(m: re.Match) -> str:
        return _PUNCT_MAP.get(m.group(0).lower(), m.group(0))
    return _PUNCT_PATTERN.sub(_replace, text)


class VoicePunctuationBuffer:
    """Handles multi-word voice commands split across Vosk streaming batches.

    Vosk's lag-N strategy delivers words in small batches. Multi-word commands
    like "question mark" may arrive as "question" in one batch and "mark" in
    the next. This buffer holds back trailing words that could be the start
    of a multi-word command, and prepends them to the next batch.

    Usage:
        buf = VoicePunctuationBuffer()
        # Each call returns text ready for injection (may be empty if buffering)
        ready = buf.process("are you there question")   # → "are you there"
        ready = buf.process("mark thank you")            # → "? thank you"
        ready = buf.flush()                               # → any remaining
    """

    def __init__(self):
        self._pending: str = ""  # word(s) held back from last batch

    def process(self, text: str) -> str:
        """Process a batch, returning text ready for punctuation + injection."""
        if self._pending:
            text = self._pending + " " + text
            self._pending = ""

        # Check if the last word is a multi-word command prefix
        words = text.split()
        if words and words[-1].lower() in _MULTI_WORD_PREFIXES:
            self._pending = words[-1]
            text = " ".join(words[:-1])

        return apply_voice_punctuation(text)

    def flush(self) -> str:
        """Flush any pending word (e.g., on silence/finalize)."""
        if self._pending:
            text = apply_voice_punctuation(self._pending)
            self._pending = ""
            return text
        return ""


class TextInjector:
    """
    Injects text at the current cursor position.

    Injection backends (auto-selected, in priority order):
      ydotool → xdotool → pynput
    """

    def __init__(self):
        self._backend = self._detect_backend()
        logger.info(f"TextInjector: using backend '{self._backend}'")
        try:
            from pynput.keyboard import Controller, Key
            self.keyboard = Controller()
            self._Key = Key
        except ImportError:
            self.keyboard = None
            self._Key = None

    # ─── Backend Detection ────────────────────────────────────────────────

    def _detect_backend(self) -> str:
        """
        Detect the best available injection backend.
        ydotool preferred: works natively on Wayland and XWayland.
        """
        try:
            subprocess.run(
                ["ydotool", "type", "--help"],
                capture_output=True, timeout=2
            )
            # Verify ydotoold daemon is running (required for ydotool)
            result = subprocess.run(
                ["pgrep", "-x", "ydotoold"],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                return "ydotool"
            else:
                logger.info("ydotool found but ydotoold daemon not running — trying xdotool")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            subprocess.run(
                ["xdotool", "version"],
                capture_output=True, timeout=2, check=True
            )
            return "xdotool"
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        return "pynput"

    # ─── Public API ──────────────────────────────────────────────────────

    def type_text(self, text: str):
        """
        Inject text at current cursor. Adds trailing space for continuity.
        Applies voice punctuation substitution before injection (P4-02).
        """
        text = text.strip()
        if not text:
            return

        # P4-02: voice punctuation substitution
        text = apply_voice_punctuation(text)

        full_text = text + " "
        logger.info(f"Injecting [{self._backend}]: '{full_text.rstrip()}'")

        if self._backend == "ydotool":
            self._inject_ydotool(full_text)
        elif self._backend == "xdotool":
            self._inject_xdotool(full_text)
        else:
            self._inject_pynput(full_text)

    def backspace(self):
        """Delete the last character."""
        if self._backend == "ydotool":
            try:
                subprocess.run(["ydotool", "key", "BackSpace"], check=True, timeout=3)
                return
            except Exception:
                pass
        try:
            subprocess.run(["xdotool", "key", "BackSpace"], check=True, timeout=3)
            return
        except Exception:
            pass
        if self.keyboard and self._Key:
            self.keyboard.press(self._Key.backspace)
            self.keyboard.release(self._Key.backspace)

    # ─── Backend Implementations ─────────────────────────────────────────

    def _inject_ydotool(self, text: str):
        """P4-01: Wayland-native injection via ydotool."""
        try:
            # ydotool type --key-delay=0 for fastest possible injection
            subprocess.run(
                ["ydotool", "type", "--key-delay=0", "--", text],
                check=True, timeout=10, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"ydotool injection failed: {e.stderr.decode()}")
            # Fall through to xdotool
            self._backend = "xdotool"
            self._inject_xdotool(text)
        except Exception as e:
            logger.error(f"ydotool unexpected error: {e}")
            self._inject_pynput(text)

    def _inject_xdotool(self, text: str):
        """X11 injection via xdotool (also works on XWayland).
        P9-01: Uses bare Popen with no capture to minimize fork overhead.
        """
        try:
            proc = subprocess.Popen(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", text],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.wait(timeout=10)
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, "xdotool")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("xdotool failed — falling back to pynput")
            self._inject_pynput(text)
        except Exception as e:
            logger.error(f"xdotool unexpected error: {e}")
            self._inject_pynput(text)

    def _inject_pynput(self, text: str):
        """Pure-Python fallback. X11 only. No Wayland support."""
        if not self.keyboard:
            logger.error("pynput keyboard not available — text injection failed")
            return
        try:
            self.keyboard.type(text)
        except Exception as e:
            logger.error(f"pynput injection failed: {e}")
