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


# Spoken numbers to digits
NUMBER_WORDS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

class SpellCorrector:
    """
    Real-time spell correction and grammar engine for ASR output.

    Pipeline:
      1. ASR artifact substitution (gonna → going to)
      2. Number conversion (one → 1)
      3. Voice Punctuation (period → .)
      4. Grammar & True Casing (Auto-capitalization & WordDB original case)
      5. SymSpell correction (for unknown typos)
    """

    def __init__(self, settings, word_db=None):
        self.settings  = settings
        self._word_db  = word_db          # WordDatabase | None
        self.enabled: bool = settings.get("spell_correction", True)
        self._sym_spell = None
        self._Verbosity = None
        self._cap_next = True             # Start of dictation is capitalized
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

            logger.info("SpellCorrector initialized (SymSpellPy + WordDatabase + Grammar)")

        except ImportError:
            logger.info("symspellpy not installed — spell correction disabled")
        except Exception as e:
            logger.error(f"SpellCorrector init error: {e}")
            self._sym_spell = None

    # ── Public API ───────────────────────────────────────────────────────────
    
    def reset_state(self):
        """Reset grammar state when a new dictation session starts."""
        self._cap_next = True

    def correct(self, text: str) -> str:
        """
        Correct a batch of words. Returns corrected text.
        Called on every finalized word batch before injection.
        """
        if not self.enabled:
            from .injection import apply_voice_punctuation
            return apply_voice_punctuation(text)

        # Step 1: ASR artifact substitution (context-free, highest priority)
        text = self._apply_asr_rules(text)
        
        # Step 2: Number conversion (words to digits)
        text = self._convert_numbers(text)

        # Step 3: Voice Punctuation mapping
        from .injection import apply_voice_punctuation
        text = apply_voice_punctuation(text)

        # Step 4: Grammar, True Casing, and Spell Correction
        words = text.split()
        corrected = []
        for word in words:
            lower = word.lower()
            
            # Punctuation boundaries trigger next-word capitalization
            if lower in {".", "?", "!", "\n", "\n\n"}:
                self._cap_next = True
                corrected.append(word)
                continue
                
            # Grammar rule: Stand-alone 'I' variations
            if lower in {"i", "i'm", "i've", "i'll", "i'd"}:
                final_word = word.capitalize()
                self._cap_next = False
                corrected.append(final_word)
                continue

            # Resolve the actual word (WordDB True Casing or SymSpell)
            final_word = word
            resolved = False
            
            if self._word_db:
                orig_case = self._word_db.get_original_case(lower)
                if orig_case:
                    final_word = orig_case
                    resolved = True
            
            if not resolved and self._sym_spell and word.isalpha() and not word[0].isupper() and not word.isupper():
                suggestions = self._sym_spell.lookup(lower, self._Verbosity.CLOSEST, max_edit_distance=2)
                if suggestions and suggestions[0].term != lower:
                    best = suggestions[0]
                    # Short word guard (preserve valid short words like 'is', 'to')
                    if len(lower) <= 3:
                        in_dict = self._sym_spell.lookup(lower, self._Verbosity.ALL, max_edit_distance=0)
                        if not in_dict and best.count > 100:
                            final_word = best.term
                    elif best.count > 100:
                        logger.debug(f"SpellCorrector: '{word}' -> '{best.term}'")
                        final_word = best.term

            # Apply Auto-Capitalization 
            if self._cap_next and len(final_word) > 0 and final_word[0].isalpha():
                final_word = final_word[0].upper() + final_word[1:]
                self._cap_next = False

            corrected.append(final_word)

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
        
    def _convert_numbers(self, text: str) -> str:
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            w_lower = words[i].lower()
            if w_lower in NUMBER_WORDS:
                val = NUMBER_WORDS[w_lower]
                # Combine tens + units (e.g. "twenty", "one" -> "21")
                if 20 <= val <= 90 and i + 1 < len(words):
                    next_w = words[i+1].lower()
                    if next_w in NUMBER_WORDS and 1 <= NUMBER_WORDS[next_w] <= 9:
                        val += NUMBER_WORDS[next_w]
                        i += 1
                result.append(str(val))
            else:
                result.append(words[i])
            i += 1
        return " ".join(result)
