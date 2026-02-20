"""
SpellCorrector — Real-time ASR post-processing for VoxInput. (Phase 3)

Corrects common ASR errors before text reaches the cursor:
  - SymSpellPy dictionary lookup (O(1), 1M+ words/sec)
  - Preserves proper nouns and capitalized words
  - User-defined custom word lists
  - Voice-to-punctuation command substitution (Phase 4 extension point)

Thread-safe: SymSpell is read-only after initialization.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Common ASR artifacts that SymSpell won't fix (context-free substitutions)
ASR_CORRECTIONS: dict[str, str] = {
    "gonna":   "going to",
    "wanna":   "want to",
    "gotta":   "got to",
    "kinda":   "kind of",
    "sorta":   "sort of",
    "lotta":   "lot of",
    "outta":   "out of",
    "shoulda": "should have",
    "coulda":  "could have",
    "woulda":  "would have",
}

# Words that should NEVER be corrected.
# Includes: tech abbreviations, proper nouns, brands, org names.
# Extend this list or use Settings -> custom_dict_path for user words.
_PASSTHROUGH: set[str] = {
    # Tech abbreviations
    "os", "ui", "ux", "vs", "api", "url", "http", "https", "html", "json",
    "ai", "ml", "db", "id", "ip", "ok", "tv", "pc", "vm", "py", "js", "css",
    "sql", "ram", "cpu", "gpu", "ssh", "git", "log", "dev", "app", "web",
    "cli", "gui", "sdk", "aws", "gcp", "dns", "tcp", "udp", "ios", "amd",
    # Proper nouns / orgs / brands that SymSpell mangles
    "nasa", "linux", "ubuntu", "debian", "google", "github", "docker",
    "python", "nvidia", "intel", "reddit", "youtube", "discord", "gmail",
    "macos", "wayland", "gnome", "kde", "vosk", "whisper", "cuda", "venv",
}



class SpellCorrector:
    """
    Real-time spell correction for ASR output.

    Initialization is lazy — if symspellpy is not installed, the corrector
    silently becomes a pass-through so the rest of the app is unaffected.
    """

    def __init__(self, settings):
        self.settings = settings
        self.enabled: bool = settings.get("spell_correction", True)   # always on by default
        self._sym_spell = None
        self._load()

    # ─── Setup ─────────────────────────────────────────────────────────────

    def _load(self):
        if not self.enabled:
            return
        try:
            from symspellpy import SymSpell, Verbosity
            self._Verbosity = Verbosity
            self._sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

            # Try bundled dictionary path (installed via symspellpy package)
            import importlib.resources as pkg
            try:
                with pkg.path("symspellpy", "frequency_dictionary_en_82_765.txt") as p:
                    self._sym_spell.load_dictionary(str(p), term_index=0, count_index=1)
            except Exception:
                # Fallback: check assets/ directory
                import os
                assets = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "assets",
                    "frequency_dictionary_en_82_765.txt"
                )
                if os.path.exists(assets):
                    self._sym_spell.load_dictionary(assets, term_index=0, count_index=1)
                else:
                    logger.warning("SpellCorrector: dictionary not found — correction disabled")
                    self._sym_spell = None
                    return

            # Optional user custom dictionary
            user_dict = self.settings.get("custom_dict_path")
            if user_dict:
                import os
                if os.path.exists(user_dict):
                    self._sym_spell.load_dictionary(user_dict, term_index=0, count_index=1)

            logger.info("SpellCorrector initialized with SymSpellPy")

        except ImportError:
            logger.info("symspellpy not installed — spell correction disabled (pip install symspellpy)")
        except Exception as e:
            logger.error(f"SpellCorrector init error: {e}")
            self._sym_spell = None

    # ─── Public API ────────────────────────────────────────────────────────

    def correct(self, text: str) -> str:
        """
        Correct a batch of words. Returns corrected text.
        Called on every word batch before injection.
        Sub-millisecond per-word overhead with SymSpell.
        """
        if not self.enabled:
            return text

        # Step 1: ASR artifact substitution (context-free, highest priority)
        text = self._apply_asr_rules(text)

        # Step 2: Dictionary-based correction (only if SymSpell loaded)
        if self._sym_spell is None:
            return text

        words = text.split()
        corrected = []
        for word in words:
            # Skip non-alpha, capitalized (proper nouns / acronyms), and ALL-CAPS
            if not word.isalpha() or word[0].isupper() or word.isupper():
                corrected.append(word)
                continue

            lower = word.lower()
            suggestions = self._sym_spell.lookup(
                lower, self._Verbosity.CLOSEST, max_edit_distance=2
            )

            # No suggestion or suggestion is same word → pass through
            if not suggestions or suggestions[0].term == lower:
                corrected.append(word)
                continue

            best = suggestions[0]

            # Never correct known short tech terms / abbreviations
            if lower in _PASSTHROUGH:
                corrected.append(word)
                continue

            # For remaining short words (<=3 chars): only correct if the word
            # is NOT in the dictionary at edit distance 0 (i.e. it's a typo).
            # 'is', 'to', 'an' etc. will be found and kept.
            # 'teh', 'adn' won't be found -> proceed to correction.
            if len(lower) <= 3:
                in_dict = self._sym_spell.lookup(lower, self._Verbosity.ALL, max_edit_distance=0)
                if in_dict:
                    corrected.append(word)
                    continue

            # Apply correction if suggestion has decent frequency
            if best.count > 100:
                logger.debug(f"SpellCorrector: '{word}' -> '{best.term}'")
                corrected.append(best.term)
            else:
                corrected.append(word)

        return " ".join(corrected)

    def reload(self):
        """Re-initialize after settings change (e.g. custom dict path updated)."""
        self._sym_spell = None
        self._load()

    # ─── Internal ──────────────────────────────────────────────────────────

    def _apply_asr_rules(self, text: str) -> str:
        """Apply VoxInput-specific ASR correction rules (no context needed)."""
        words = text.split()
        return " ".join(ASR_CORRECTIONS.get(w.lower(), w) for w in words)
