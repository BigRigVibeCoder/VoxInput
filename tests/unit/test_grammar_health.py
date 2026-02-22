"""
tests/unit/test_grammar_health.py — Grammar Engine Health Check
================================================================
Standalone test that verifies all grammar engine components are online
and functioning correctly. Tests ASR corrections, number conversion
(with context awareness), capitalization, and the full pipeline.

This test does NOT depend on audio or Vosk — it exercises the
SpellCorrector directly.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.spell_corrector import SpellCorrector
from src.injection import VoicePunctuationBuffer, apply_voice_punctuation


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _sc():
    """SpellCorrector with real SettingsManager."""
    from src.settings import SettingsManager
    return SpellCorrector(SettingsManager())

def _convert_and_flush(sc, text):
    """Convert numbers and flush pending state (simulates single-batch + silence)."""
    result = sc._convert_numbers(text)
    flushed = sc.flush_pending_number()
    parts = [p for p in [result, flushed] if p]
    return " ".join(parts) if parts else ""


# ─── 1. Engine Online ────────────────────────────────────────────────────────

class TestEngineOnline:
    """Verify core grammar engine components load successfully."""

    def test_spell_corrector_initializes(self):
        sc = _sc()
        assert sc is not None
        assert sc.enabled is True

    def test_symspell_loaded(self):
        sc = _sc()
        sc.correct("test")  # P9-05: trigger lazy load
        assert sc._sym_spell is not None, "SymSpell dictionary failed to load"

    def test_asr_rules_apply(self):
        sc = _sc()
        assert "going to" in sc.correct("gonna").lower()

    def test_number_converter_works(self):
        sc = _sc()
        result = sc.correct("one hundred")
        flushed = sc.flush_pending_number()
        combined = f"{result} {flushed}".strip()
        assert "100" in combined


# ─── 2. Capitalization Rules ─────────────────────────────────────────────────

class TestCapitalization:
    """Verify auto-capitalization rules."""

    def test_sentence_start_capitalized(self):
        sc = _sc()
        result = sc.correct("hello world")
        assert result[0].isupper(), f"Sentence start not capitalized: '{result}'"

    def test_i_always_capitalized(self):
        sc = _sc()
        result = sc.correct("i think i'm right")
        words = result.split()
        for w in words:
            if w.lower() in ("i", "i'm", "i've", "i'll", "i'd"):
                assert w[0] == "I", f"'{w}' should be capitalized"

    def test_cap_after_period_word(self):
        sc = _sc()
        result = sc.correct("good period the end")
        # The word after "period" should be capitalized
        words = result.split()
        period_idx = next((i for i, w in enumerate(words) if w.lower() == "period"), None)
        if period_idx is not None and period_idx + 1 < len(words):
            next_word = words[period_idx + 1]
            assert next_word[0].isupper(), f"Word after 'period' not capitalized: '{next_word}'"

    def test_cap_after_question_word(self):
        sc = _sc()
        sc._cap_next = False  # Reset to avoid start-of-sentence cap
        result = sc.correct("really question the next")
        words = result.split()
        q_idx = next((i for i, w in enumerate(words) if w.lower() == "question"), None)
        if q_idx is not None and q_idx + 1 < len(words):
            next_word = words[q_idx + 1]
            assert next_word[0].isupper(), f"Word after 'question' not capitalized: '{next_word}'"


# ─── 3. Context-Aware Numbers ────────────────────────────────────────────────

class TestContextAwareNumbers:
    """Verify numbers convert based on context."""

    def test_two_apples_stays_words(self):
        sc = _sc()
        result = _convert_and_flush(sc,"two apples")
        assert "two" in result.lower(), f"'two apples' should stay as words, got: '{result}'"

    def test_three_errors_stays_words(self):
        sc = _sc()
        result = _convert_and_flush(sc,"three errors")
        assert "three" in result.lower(), f"'three errors' should stay as words, got: '{result}'"

    def test_eight_pieces_stays_words(self):
        sc = _sc()
        result = _convert_and_flush(sc,"eight pieces")
        assert "eight" in result.lower()

    def test_chapter_two_converts(self):
        sc = _sc()
        result = _convert_and_flush(sc,"chapter two")
        assert "2" in result, f"'chapter two' should become 'chapter 2', got: '{result}'"

    def test_section_nine_converts(self):
        sc = _sc()
        result = _convert_and_flush(sc,"section nine")
        assert "9" in result, f"'section nine' should become 'section 9', got: '{result}'"

    def test_one_hundred_still_converts(self):
        sc = _sc()
        result = _convert_and_flush(sc,"one hundred")
        assert "100" in result

    def test_twenty_one_still_converts(self):
        sc = _sc()
        result = _convert_and_flush(sc,"twenty one")
        assert "21" in result

    def test_forty_seven_converts(self):
        sc = _sc()
        result = _convert_and_flush(sc,"forty seven")
        assert "47" in result

    def test_ordinal_twenty_first(self):
        sc = _sc()
        result = _convert_and_flush(sc,"twenty first")
        assert "21st" in result


# ─── 4. Voice Punctuation Buffer ─────────────────────────────────────────────

class TestVoicePunctuationBuffer:
    """Verify cross-batch voice command buffering."""

    def test_question_mark_split_across_batches(self):
        buf = VoicePunctuationBuffer()
        r1 = buf.process("are you there question")
        assert "question" not in r1.lower()  # buffered
        r2 = buf.process("mark thank you")
        assert "?" in r2

    def test_new_line_split_across_batches(self):
        buf = VoicePunctuationBuffer()
        r1 = buf.process("hello new")
        assert "new" not in r1.lower()  # buffered
        r2 = buf.process("line world")
        assert "\n" in r2

    def test_flush_pending_word(self):
        buf = VoicePunctuationBuffer()
        r1 = buf.process("last word question")
        assert "question" not in r1.lower()
        flushed = buf.flush()
        assert flushed  # "question" by itself doesn't match, flushed as-is

    def test_no_buffer_needed(self):
        buf = VoicePunctuationBuffer()
        result = buf.process("hello comma world")
        assert "," in result


# ─── 5. Nightmare Paragraph ─────────────────────────────────────────────────

class TestNightmareParagraph:
    """Full pipeline test with the homophone nightmare paragraph."""

    def test_homophones_and_context_numbers(self):
        sc = _sc()
        buf = VoicePunctuationBuffer()

        chunks = [
            "it was too late to buy two apples",
            "comma so they are going over there to grab their pears instead",
            "period he ate eight pieces of meat",
        ]

        full = []
        for chunk in chunks:
            corrected = sc.correct(chunk)
            punctuated = buf.process(corrected)
            if punctuated:
                full.append(punctuated)
        flushed = buf.flush()
        if flushed:
            full.append(flushed)

        result = " ".join(full)

        # Context-aware: "two apples" stays as words
        assert "two" in result.lower() or "2 apples" not in result
        # Voice punctuation works
        assert "," in result
        assert "." in result
        # "eight pieces" should stay as "eight" (small number + noun)
        assert "eight" in result.lower() or "8 pieces" not in result
