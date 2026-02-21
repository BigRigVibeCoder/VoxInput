"""
tests/unit/test_pipeline_integration.py — Pipeline Integration Tests
=====================================================================
Tests the full spell-correction pipeline that runs AFTER Vosk recognition
and BEFORE text injection. Covers:

  1. Number conversion   (one hundred twenty three → 123)
  2. Dictionary database  (protected words preserved, True Casing)
  3. Voice punctuation    (period → ., new line → \n, etc.)
  4. Grammar rules        (I/I'm capitalization, cap-after-period)
  5. ASR artifact cleanup (gonna → going to, wanna → want to)

Regression targets:
  - Numbers not converting to digits
  - Protected words being spell-corrected into common words
  - Voice punctuation commands appearing as literal text
"""
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.spell_corrector import SpellCorrector
from src.injection import apply_voice_punctuation


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_corrector(enabled=True):
    """Create a SpellCorrector with spell correction enabled/disabled."""
    settings = MagicMock()
    settings.get = MagicMock(return_value=enabled)
    return SpellCorrector(settings)


# ─── 1. Number Conversion ────────────────────────────────────────────────────

class TestNumberConversion:
    """Verify _convert_numbers converts spoken numbers to digits."""

    def test_single_digits(self):
        sc = _make_corrector()
        assert sc._convert_numbers("one two three") == "1 2 3"

    def test_teens(self):
        sc = _make_corrector()
        # Consecutive number words chain into compounds (dictation behavior)
        result = sc._convert_numbers("eleven")
        assert result == "11"
        result = sc._convert_numbers("thirteen")
        assert result == "13"

    def test_tens(self):
        sc = _make_corrector()
        # Individual tens in isolation
        assert sc._convert_numbers("twenty") == "20"
        assert sc._convert_numbers("thirty") == "30"
        assert sc._convert_numbers("forty") == "40"

    def test_compound_tens(self):
        sc = _make_corrector()
        assert sc._convert_numbers("twenty one") == "21"
        assert sc._convert_numbers("forty five") == "45"
        assert sc._convert_numbers("ninety nine") == "99"

    def test_hundreds(self):
        sc = _make_corrector()
        assert sc._convert_numbers("one hundred") == "100"
        assert sc._convert_numbers("two hundred and fifteen") == "215"
        assert sc._convert_numbers("three hundred forty five") == "345"

    def test_thousands(self):
        sc = _make_corrector()
        assert sc._convert_numbers("one thousand") == "1000"
        assert sc._convert_numbers("five thousand two hundred") == "5200"

    def test_numbers_in_context(self):
        sc = _make_corrector()
        result = sc._convert_numbers("i have forty seven errors")
        assert "47" in result
        assert "errors" in result

    def test_phone_number_digits(self):
        sc = _make_corrector()
        result = sc._convert_numbers("five five five one two three four")
        # Single digits should stay individual: 5 5 5 1 2 3 4
        digits = [d for d in result.split() if d.isdigit()]
        assert len(digits) == 7

    def test_non_number_passthrough(self):
        sc = _make_corrector()
        assert sc._convert_numbers("hello world") == "hello world"

    def test_ordinal_first(self):
        sc = _make_corrector()
        assert sc._convert_numbers("first") == "1st"

    def test_ordinal_third(self):
        sc = _make_corrector()
        assert sc._convert_numbers("third") == "3rd"

    def test_ordinal_twenty_first(self):
        sc = _make_corrector()
        assert sc._convert_numbers("twenty first") == "21st"

    def test_ordinal_hundred_and_third(self):
        sc = _make_corrector()
        assert sc._convert_numbers("one hundred and third") == "103rd"

    def test_ordinal_in_context(self):
        sc = _make_corrector()
        result = sc._convert_numbers("march twenty first")
        assert "21st" in result
        assert "march" in result


# ─── 2. Voice Punctuation ────────────────────────────────────────────────────

class TestVoicePunctuation:
    """Verify voice commands are converted to actual punctuation."""

    def test_period(self):
        result = apply_voice_punctuation("hello period")
        assert "." in result
        assert "period" not in result.lower()

    def test_comma(self):
        result = apply_voice_punctuation("hello comma world")
        assert "," in result

    def test_question_mark(self):
        result = apply_voice_punctuation("are you there question mark")
        assert "?" in result

    def test_exclamation_mark(self):
        result = apply_voice_punctuation("warning exclamation mark")
        assert "!" in result

    def test_exclamation_point(self):
        result = apply_voice_punctuation("warning exclamation point")
        assert "!" in result

    def test_new_line(self):
        result = apply_voice_punctuation("line one new line line two")
        assert "\n" in result

    def test_new_paragraph(self):
        result = apply_voice_punctuation("paragraph one new paragraph paragraph two")
        assert "\n\n" in result

    def test_colon(self):
        result = apply_voice_punctuation("items colon")
        assert ":" in result

    def test_semicolon(self):
        result = apply_voice_punctuation("first semicolon second")
        assert ";" in result

    def test_multiple_punctuation(self):
        """Multiple commands in one string."""
        result = apply_voice_punctuation(
            "hello comma how are you question mark"
        )
        assert "," in result
        assert "?" in result


# ─── 3. Full Pipeline (correct method) ───────────────────────────────────────

class TestFullPipeline:
    """Test the complete correct() pipeline: ASR rules → numbers → punctuation → grammar."""

    def test_numbers_and_punctuation_together(self):
        sc = _make_corrector()
        result = sc.correct("i have forty seven errors period")
        assert "47" in result
        assert "." in result

    def test_i_capitalization(self):
        sc = _make_corrector()
        result = sc.correct("i think i'm going to the store")
        words = result.split()
        # Find all instances of i/I and i'm/I'm
        for w in words:
            if w.lower() in ("i", "i'm", "i've", "i'll", "i'd"):
                assert w[0] == "I", f"'{w}' should be capitalized"

    def test_cap_after_period(self):
        sc = _make_corrector()
        result = sc.correct("hello period the next word")
        # After ., the next alphabetic word should be capitalized
        parts = result.split(".")
        if len(parts) > 1:
            after = parts[1].strip()
            if after:
                assert after[0].isupper(), f"Word after period should be capitalized: '{after}'"

    def test_asr_gonna_correction(self):
        sc = _make_corrector()
        result = sc.correct("i gonna go")
        assert "gonna" not in result.lower()

    def test_asr_wanna_correction(self):
        sc = _make_corrector()
        result = sc.correct("i wanna eat")
        assert "wanna" not in result.lower()

    def test_complex_dictation(self):
        """Simulate a real dictation with numbers, punctuation, and grammar."""
        sc = _make_corrector()
        result = sc.correct(
            "dear mr thompson comma i am writing to confirm "
            "your appointment on march twenty first period"
        )
        # 'twenty first' → '21st' (ordinal support)
        assert "21st" in result  # number + ordinal conversion
        assert "," in result       # comma punctuation
        assert "." in result       # period punctuation
        assert "I am" in result    # I capitalization


# ─── 4. Dictionary Database ──────────────────────────────────────────────────

class TestDictionaryIntegration:
    """Test that the WordDatabase protects known words from spell correction."""

    def test_word_db_hookup(self):
        """SpellCorrector accepts a word_db and uses it."""
        sc = _make_corrector()
        mock_db = MagicMock()
        mock_db.get_original_case = MagicMock(return_value="VoxInput")
        sc.set_word_db(mock_db)
        result = sc.correct("voxinput is great")
        mock_db.get_original_case.assert_called()

    def test_word_db_preserves_casing(self):
        """Words in the dictionary should use the DB's True Casing."""
        sc = _make_corrector()
        mock_db = MagicMock()
        # When asked about "python", return "Python" (True Cased)
        mock_db.get_original_case = MagicMock(
            side_effect=lambda w: "Python" if w == "python" else None
        )
        sc.set_word_db(mock_db)
        result = sc.correct("python is great")
        assert "Python" in result

    def test_real_word_db_loads(self):
        """The actual custom_words.db file exists and loads."""
        from src.word_db import WordDatabase
        db_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "custom_words.db"
        )
        if os.path.exists(db_path):
            db = WordDatabase(db_path)
            assert db is not None
        else:
            pytest.skip("custom_words.db not found")
