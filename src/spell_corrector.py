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


# Spoken numbers semantic tokens
NUMBER_UNITS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
NUMBER_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
NUMBER_SCALES = ["hundred", "thousand", "million", "billion", "trillion"]

# Build parsing map
NUM_DICT = {}
for idx, word in enumerate(NUMBER_UNITS):    NUM_DICT[word] = (1, idx)
for idx, word in enumerate(NUMBER_TENS):
    if word: NUM_DICT[word] = (1, idx * 10)
for idx, word in enumerate(NUMBER_SCALES):   NUM_DICT[word] = (10 ** (idx * 3 or 2), 0)

# Ordinal number words → (numeric_value, suffix)
ORDINAL_DICT = {
    "first": (1, "st"), "second": (2, "nd"), "third": (3, "rd"),
    "fourth": (4, "th"), "fifth": (5, "th"), "sixth": (6, "th"),
    "seventh": (7, "th"), "eighth": (8, "th"), "ninth": (9, "th"),
    "tenth": (10, "th"), "eleventh": (11, "th"), "twelfth": (12, "th"),
    "thirteenth": (13, "th"), "fourteenth": (14, "th"), "fifteenth": (15, "th"),
    "sixteenth": (16, "th"), "seventeenth": (17, "th"), "eighteenth": (18, "th"),
    "nineteenth": (19, "th"), "twentieth": (20, "th"), "thirtieth": (30, "th"),
    "fortieth": (40, "th"), "fiftieth": (50, "th"), "sixtieth": (60, "th"),
    "seventieth": (70, "th"), "eightieth": (80, "th"), "ninetieth": (90, "th"),
    "hundredth": (100, "th"), "thousandth": (1000, "th"),
}


def _ordinal_suffix(n: int) -> str:
    """Return the English ordinal suffix for a number (1→st, 2→nd, 3→rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


class SpellCorrector:
    """
    Real-time spell correction and grammar engine for ASR output.

    Pipeline:
      1. ASR artifact substitution (gonna → going to)
      2. Complex Number parsing (one hundred -> 100, twenty first -> 21st)
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
        # Cross-batch number accumulator state
        self._num_result = 0
        self._num_current = 0
        self._num_pending_words: list[str] = []  # original words held back
        self._loaded = False               # P9-05: lazy load gate

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

            # Inject custom WordDatabase words into SymSpell as high-frequency
            # correction targets. Without this, SymSpell only corrects against
            # the generic English dictionary and ignores custom tech terms.
            if self._word_db and self._word_db._dict:
                injected = 0
                for lower_word in self._word_db._dict:
                    self._sym_spell.create_dictionary_entry(lower_word, 1_000_000)
                    injected += 1
                if injected:
                    logger.info(f"SpellCorrector: injected {injected} custom words into SymSpell")

            logger.info("SpellCorrector initialized (SymSpellPy + WordDatabase + Grammar + ParseNum)")

        except ImportError:
            logger.info("symspellpy not installed — spell correction disabled")
        except Exception as e:
            logger.error(f"SpellCorrector init error: {e}")
            self._sym_spell = None

    # ── Public API ───────────────────────────────────────────────────────────
    
    def reset_state(self):
        """Reset grammar state when a new dictation session starts."""
        self._cap_next = True
        self._num_result = 0
        self._num_current = 0
        self._num_pending_words = []

    def flush_pending_number(self) -> str:
        """Flush any accumulated number from cross-batch buffering."""
        if self._num_pending_words:
            total = self._num_result + self._num_current
            self._num_result = 0
            self._num_current = 0
            self._num_pending_words = []
            return str(total)
        return ""

    def correct(self, text: str) -> str:
        """
        Correct a batch of words. Returns corrected text.
        Called on every finalized word batch before injection.
        """
        if not self.enabled:
            return text

        # P9-05: lazy-load SymSpell on first correction (saves ~2s startup)
        if not self._loaded:
            self._load()
            self._loaded = True

        # Step 0: Phonetic compound correction (multi-word ASR misrecognitions)
        text = self._apply_compound_corrections(text)

        # Step 1: ASR artifact substitution (context-free, highest priority)
        text = self._apply_asr_rules(text)
        
        # Step 2: Complex number conversion (hundreds, thousands, millions, ordinals)
        text = self._convert_numbers(text)

        # Step 3: Grammar, True Casing, and Spell Correction
        words = text.split()
        corrected = []
        for word in words:
            lower = word.lower()
            
            # Punctuation boundaries trigger next-word capitalization
            # Includes both actual chars AND voice command words (punctuation
            # is now applied downstream by VoicePunctuationBuffer)
            if lower in {".", "?", "!", "\n", "\n\n",
                          "period", "full stop", "question", "exclamation"}:
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
                # Protect common abbreviations from being "corrected"
                _PROTECTED = {"mr", "mrs", "ms", "dr", "sr", "jr", "vs", "st",
                              "ft", "mt", "id", "ok", "pm", "am", "tv", "uk", "us",
                              "hundred", "thousand", "million", "billion", "trillion"}
                if lower not in _PROTECTED:
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

        result = " ".join(corrected)

        # P9-C: Phrase-level correction (2-word compound lookup)
        # Preserves original capitalization since lookup_compound lowercases
        # Skip if text contains abbreviations that lookup_compound would corrupt
        _COMPOUND_SKIP = {
            "mr", "mrs", "ms", "dr", "sr", "jr", "vs", "st", "ft", "mt", "id", "ok",
            # Number words — lookup_compound corrupts these (e.g. "hundred" → "a of")
            "hundred", "thousand", "million", "billion", "trillion",
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen",
            "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
        }
        has_abbrev = any(w.lower().rstrip('.,;:!?') in _COMPOUND_SKIP for w in corrected)
        has_digits = any(any(c.isdigit() for c in w) for w in corrected)
        if self._sym_spell and len(corrected) >= 2 and not has_abbrev and not has_digits:
            try:
                compound = self._sym_spell.lookup_compound(result, max_edit_distance=2)
                if compound and compound[0].distance > 0 and compound[0].count > 0:
                    new_words = compound[0].term.split()
                    old_words = result.split()
                    # Re-apply original capitalization
                    restored = []
                    for i, nw in enumerate(new_words):
                        if i < len(old_words) and old_words[i][0].isupper():
                            nw = nw[0].upper() + nw[1:]
                        restored.append(nw)
                    result = " ".join(restored)
            except Exception:
                pass  # lookup_compound can fail on edge cases

        return result

    def set_word_db(self, word_db):
        """Hot-swap the WordDatabase (called after lazy load in main.py)."""
        self._word_db = word_db

    def reload(self):
        """Re-initialize after settings change."""
        self._sym_spell = None
        self._load()

    # ── Internal ─────────────────────────────────────────────────────────────

    # Phonetic compound map: multi-word ASR misrecognitions → correct term.
    # Vosk splits unknown tech terms into phonetically similar English words.
    # SymSpell can't reach these (edit distance >> 2 between the fragments).
    # Keys are lowercase tuples of misheard words.
    _COMPOUND_MAP: dict[tuple[str, ...], str] = {
        # Infrastructure
        ("cooper", "netty's"): "kubernetes",
        ("cooper", "nettie's"): "kubernetes",
        ("cooper", "neediest"): "kubernetes",
        ("cube", "control"): "kubectl",
        ("and", "simple"): "ansible",
        ("engine", "next"): "nginx",
        ("engine", "x"): "nginx",
        ("pie", "torch"): "PyTorch",
        ("tensor", "flow"): "TensorFlow",
        ("tail", "scale"): "Tailscale",
        ("terra", "form"): "Terraform",
        ("read", "is"): "Redis",
        ("post", "gress"): "Postgres",
        ("graph", "queue", "l"): "GraphQL",
        ("graph", "q", "l"): "GraphQL",
        ("type", "script"): "TypeScript",
        ("java", "script"): "JavaScript",
        ("next", "j", "s"): "Next.js",
        ("ex", "tool"): "xdotool",
        ("sim", "spell"): "SymSpell",
        ("pi", "input"): "pynput",
        ("vox", "input"): "VoxInput",
        ("hive", "mind"): "HiveMind",
        ("oh", "droid"): "ODROID",
        ("lie", "dar"): "LIDAR",
        ("li", "dar"): "LIDAR",
        # Common API/tech
        ("a", "p", "i"): "API",
        ("a", "pr"): "API",
        ("a", "p", "r"): "API",
        ("see", "i"): "CI",
        ("see", "d"): "CD",
    }

    def _apply_compound_corrections(self, text: str) -> str:
        """Replace multi-word ASR misrecognitions with correct terms.

        Uses sliding window (2-3 words) against _COMPOUND_MAP.
        Runs BEFORE SymSpell so the corrected single words can then
        be true-cased by WordDB.
        """
        words = text.split()
        if len(words) < 2:
            return text

        result = []
        i = 0
        while i < len(words):
            matched = False
            # Try 3-word match first, then 2-word
            for window in (3, 2):
                if i + window <= len(words):
                    key = tuple(w.lower() for w in words[i:i+window])
                    if key in self._COMPOUND_MAP:
                        replacement = self._COMPOUND_MAP[key]
                        logger.debug(f"CompoundFix: {' '.join(words[i:i+window])} → {replacement}")
                        result.append(replacement)
                        i += window
                        matched = True
                        break
            if not matched:
                result.append(words[i])
                i += 1

        return " ".join(result)

    def _apply_asr_rules(self, text: str) -> str:
        words = text.split()
        return " ".join(ASR_CORRECTIONS.get(w.lower(), w) for w in words)
        
    def _convert_numbers(self, text: str) -> str:
        current = self._num_current
        result = self._num_result
        in_number = bool(self._num_pending_words)
        tokens = text.split()
        output = []

        # Words that signal the following number should stay as digits
        _ORDINAL_TRIGGERS = {"chapter", "section", "item", "page", "step",
                             "number", "no", "version", "level", "grade",
                             "type", "phase", "part", "option", "rule"}

        i = 0
        while i < len(tokens):
            word = tokens[i].lower()

            is_num = word in NUM_DICT
            is_ordinal = word in ORDINAL_DICT
            is_and = word == "and"

            valid_and = False
            if is_and and in_number and i + 1 < len(tokens):
                next_word = tokens[i+1].lower()
                if next_word in NUM_DICT or next_word in ORDINAL_DICT:
                    valid_and = True

            # Context-aware: small numbers (one–ten) before a non-number
            # word are likely quantity adjectives ("two apples"), keep as words.
            # BUT convert if preceded by trigger words ("chapter two" → 2)
            # or followed by another number word ("one hundred" → 100).
            if is_num and not in_number:
                scale, increment = NUM_DICT[word]
                # Only applies to units (one–nineteen, scale==1)
                if scale == 1 and increment <= 19:
                    next_word = tokens[i+1].lower() if i + 1 < len(tokens) else ""
                    prev_word = output[-1].lower() if output else ""
                    next_is_number = next_word in NUM_DICT or next_word in ORDINAL_DICT or next_word == "and"
                    prev_is_trigger = prev_word in _ORDINAL_TRIGGERS
                    has_follower = i + 1 < len(tokens)
                    if has_follower and not next_is_number and not prev_is_trigger:
                        # Keep as a word — it's a quantity adjective (e.g., "two apples")
                        output.append(tokens[i])
                        i += 1
                        continue
                    
            if not is_num and not is_ordinal and not valid_and:
                if in_number:
                    output.append(str(result + current))
                    result = current = 0
                    in_number = False
                output.append(tokens[i])
            elif is_ordinal:
                # Ordinal — finalize with suffix
                ord_val, _ = ORDINAL_DICT[word]
                total = result + current + ord_val
                suffix = _ordinal_suffix(total)
                output.append(f"{total}{suffix}")
                result = current = 0
                in_number = False
            else:
                in_number = True
                if not valid_and:
                    scale, increment = NUM_DICT[word]
                    
                    # Check for strings of single digits (one two three -> 1 2 3) and years (19 99)
                    if scale == 1 and current > 0 and current < 100 and increment < 100:
                        if current < 100 and increment >= 10 and current >= 10:
                            current = current * 100 + increment
                        elif current < 10 and increment < 10:
                            output.append(str(result + current))
                            result = 0
                            current = increment
                        elif current < 10 and increment >= 20:
                            # "three forty" = separate numbers (time), not 43
                            output.append(str(result + current))
                            result = 0
                            current = increment
                        else:
                            current += increment
                    elif scale == 100:
                        current = max(1, current) * scale
                    elif scale > 100:
                        result += max(1, current) * scale
                        current = 0
                    else:
                        current += increment
            i += 1
            
        if in_number:
            # Don't emit yet — hold back for potential continuation
            self._num_result = result
            self._num_current = current
            self._num_pending_words.extend(
                t for t in tokens if t.lower() in NUM_DICT or t.lower() in ORDINAL_DICT or t.lower() == "and"
            )
        else:
            self._num_result = 0
            self._num_current = 0
            self._num_pending_words = []

        return " ".join(output)

