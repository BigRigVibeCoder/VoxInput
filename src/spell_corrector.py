"""
SpellCorrector — Real-time ASR post-processing for VoxInput.

Pipeline per word batch:
  1. ASR artifact substitution (gonna→going to, etc.)
  2. WordDatabase passthrough check  (O(1) set lookup)
  3. SymSpell dictionary correction  (edit-distance ≤ 2)

Thread-safe: SymSpell is read-only after init. WordDatabase uses its own lock.
"""
import logging

logger = logging.getLogger(__name__)

# Context-free ASR artifact substitutions — highest priority, always applied.
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


class SpellCorrector:
    """
    Real-time spell correction for ASR output.

    If symspellpy is not installed, silently passes text through.
    If word_db is provided, words in the database are never corrected.
    """

    def __init__(self, settings, word_db=None):
        self.settings  = settings
        self._word_db  = word_db          # WordDatabase | None
        self.enabled: bool = settings.get("spell_correction", True)
        self._sym_spell = None
        self._Verbosity = None
        self._load()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _load(self):
        if not self.enabled:
            return
        try:
            from symspellpy import SymSpell, Verbosity
            self._Verbosity = Verbosity
            self._sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

            import importlib.resources as pkg
            try:
                with pkg.path("symspellpy", "frequency_dictionary_en_82_765.txt") as p:
                    self._sym_spell.load_dictionary(str(p), term_index=0, count_index=1)
            except Exception:
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

            user_dict = self.settings.get("custom_dict_path")
            if user_dict:
                import os
                if os.path.exists(user_dict):
                    self._sym_spell.load_dictionary(user_dict, term_index=0, count_index=1)

            logger.info("SpellCorrector initialized (SymSpellPy + WordDatabase)")

        except ImportError:
            logger.info("symspellpy not installed — spell correction disabled")
        except Exception as e:
            logger.error(f"SpellCorrector init error: {e}")
            self._sym_spell = None

    # ── Public API ───────────────────────────────────────────────────────────

    def correct(self, text: str) -> str:
        """
        Correct a batch of words. Returns corrected text.
        Called on every finalized word batch before injection.
        """
        if not self.enabled:
            return text

        # Step 1: ASR artifact substitution (context-free, highest priority)
        text = self._apply_asr_rules(text)

        # Step 2: SymSpell word-level correction
        if self._sym_spell is None:
            return text

        words = text.split()
        corrected = []
        for word in words:
            lower = word.lower()

            # Skip ALL-CAPS and capitalized words (proper nouns / acronyms)
            if not word.isalpha() or word[0].isupper() or word.isupper():
                corrected.append(word)
                continue

            # Skip words in the protected WordDatabase
            if self._word_db and self._word_db.is_protected(lower):
                corrected.append(word)
                continue

            suggestions = self._sym_spell.lookup(
                lower, self._Verbosity.CLOSEST, max_edit_distance=2
            )

            # No suggestion or suggestion is identical → keep as-is
            if not suggestions or suggestions[0].term == lower:
                corrected.append(word)
                continue

            best = suggestions[0]

            # For short words (≤3 chars): only correct if the word is NOT in
            # the SymSpell dictionary at edit_distance=0. Real words like
            # 'is','to','an' exist there; typos like 'teh','adn' do not.
            if len(lower) <= 3:
                in_dict = self._sym_spell.lookup(
                    lower, self._Verbosity.ALL, max_edit_distance=0
                )
                if in_dict:
                    corrected.append(word)
                    continue

            # Apply if suggestion has meaningful frequency (avoids obscure replacements)
            if best.count > 100:
                logger.debug(f"SpellCorrector: '{word}' -> '{best.term}'")
                corrected.append(best.term)
            else:
                corrected.append(word)

        return " ".join(corrected)

    def set_word_db(self, word_db):
        """Hot-swap the WordDatabase (called after lazy load in main.py)."""
        self._word_db = word_db

    def reload(self):
        """Re-initialize after settings change."""
        self._sym_spell = None
        self._load()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _apply_asr_rules(self, text: str) -> str:
        words = text.split()
        return " ".join(ASR_CORRECTIONS.get(w.lower(), w) for w in words)
