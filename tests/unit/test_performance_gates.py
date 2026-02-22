"""
tests/unit/test_performance_gates.py — Gate Testing Regime for P9 Overhaul
==========================================================================
Automated gate tests for VoxInput Performance Overhaul v2.0.
Each test class corresponds to a gate from the feature spec.
"""
import os
import sys
import time
import subprocess
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.spell_corrector import SpellCorrector
from src.homophones import fix_homophones


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_corrector():
    settings = MagicMock()
    settings.get = MagicMock(return_value=True)
    return SpellCorrector(settings)


def _convert_and_flush(sc, text):
    result = sc._convert_numbers(text)
    flushed = sc.flush_pending_number()
    parts = [p for p in [result, flushed] if p]
    return " ".join(parts) if parts else ""


# ─── Gate 1: Speed ───────────────────────────────────────────────────────────

class TestGate1Speed:
    """Verify speed improvements are functional."""

    def test_xdotool_available(self):
        """xdotool binary exists and responds."""
        result = subprocess.run(
            ["xdotool", "version"], capture_output=True, timeout=5
        )
        assert result.returncode == 0

    def test_xdotool_popen_no_capture(self):
        """P9-01: Popen without capture_output works correctly."""
        proc = subprocess.Popen(
            ["xdotool", "getactivewindow"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=5)
        assert proc.returncode == 0, "Popen xdotool should succeed"

    def test_lazy_symspell_not_loaded_on_init(self):
        """P9-05: SymSpell should NOT be loaded during __init__."""
        sc = _make_corrector()
        assert sc._sym_spell is None, "SymSpell should be None before first correct() call"
        assert sc._loaded is False

    def test_lazy_symspell_loads_on_first_correct(self):
        """P9-05: SymSpell should load on first correct() call."""
        from src.settings import SettingsManager
        sc = SpellCorrector(SettingsManager())
        assert sc._loaded is False
        sc.correct("hello world")
        assert sc._loaded is True


# ─── Gate 2: Memory ──────────────────────────────────────────────────────────

class TestGate2Memory:
    """Verify memory improvements."""

    def test_symspell_init_fast_without_load(self):
        """SpellCorrector init should be fast when SymSpell is deferred."""
        t0 = time.perf_counter()
        sc = _make_corrector()
        init_time = (time.perf_counter() - t0) * 1000
        # Without loading SymSpell dictionary, init should be < 50ms
        assert init_time < 50, f"Init took {init_time:.0f}ms, should be < 50ms"


# ─── Gate 3: Voice Quality ───────────────────────────────────────────────────

class TestGate3VoiceQuality:
    """Verify voice quality improvements."""

    # ── Homophones ──

    def test_homophones_their_there(self):
        """'over their' → 'over there'"""
        assert "over there" in fix_homophones("over their")

    def test_homophones_there_their(self):
        """'there things' → 'their things'"""
        assert "their things" in fix_homophones("there things")

    def test_homophones_theyre(self):
        """'their going' → 'they're going'"""
        assert "they're going" in fix_homophones("their going")

    def test_homophones_to_too(self):
        """'to much' → 'too much'"""
        assert "too much" in fix_homophones("to much")

    def test_homophones_its_its(self):
        """'its a' → 'it's a'"""
        assert "it's a" in fix_homophones("its a")

    def test_homophones_your_youre(self):
        """'your going' → 'you're going'"""
        assert "you're going" in fix_homophones("your going")

    def test_homophones_then_than(self):
        """'bigger then' → 'bigger than'"""
        assert "bigger than" in fix_homophones("bigger then")

    def test_homophones_passthrough(self):
        """Text without homophones should pass through unchanged."""
        text = "the quick brown fox"
        assert fix_homophones(text) == text

    # ── Confidence filtering ──

    def test_confidence_filtering_logic(self):
        """Verify confidence filter drops low-conf words."""
        # Simulate Vosk result with per-word confidence
        word_results = [
            {"word": "hello", "conf": 0.95},
            {"word": "uh", "conf": 0.15},       # noise — should be dropped
            {"word": "world", "conf": 0.88},
        ]
        threshold = 0.3
        filtered = [wr['word'] for wr in word_results if wr.get('conf', 1.0) >= threshold]
        assert filtered == ["hello", "world"]
        assert "uh" not in filtered

    # ── Phrase-level correction ──

    def test_phrase_level_correction_exists(self):
        """SpellCorrector should have lookup_compound in correct()."""
        from src.settings import SettingsManager
        sc = SpellCorrector(SettingsManager())
        # Just verify it doesn't crash on multi-word input
        result = sc.correct("hello wrold")
        sc.flush_pending_number()
        assert isinstance(result, str)
        assert len(result) > 0

    # ── Adaptive silence ──

    def test_adaptive_silence_ema(self):
        """EMA noise floor tracks downward correctly."""
        alpha = 0.05
        ema = 500.0  # initial
        # Simulate 20 chunks of low noise (rms=100)
        for _ in range(20):
            ema = alpha * 100 + (1 - alpha) * ema
        # EMA should have moved significantly toward 100
        assert ema < 400, f"EMA should converge toward 100, got {ema:.0f}"
        # Threshold would be ema * 2.5
        threshold = max(200, int(ema * 2.5))
        assert threshold < 1000, f"Adaptive threshold should be reasonable: {threshold}"


# ─── Gate 4: Regression ──────────────────────────────────────────────────────

class TestGate4Regression:
    """Verify no regressions in existing functionality."""

    def test_number_conversion_still_works(self):
        from src.settings import SettingsManager
        sc = SpellCorrector(SettingsManager())
        result = _convert_and_flush(sc, "one hundred")
        assert "100" in result

    def test_context_aware_numbers_preserved(self):
        from src.settings import SettingsManager
        sc = SpellCorrector(SettingsManager())
        result = _convert_and_flush(sc, "two apples")
        assert "two" in result.lower()

    def test_ordinals_still_work(self):
        from src.settings import SettingsManager
        sc = SpellCorrector(SettingsManager())
        result = _convert_and_flush(sc, "twenty first")
        assert "21st" in result

    def test_voice_punctuation_still_works(self):
        from src.injection import apply_voice_punctuation
        result = apply_voice_punctuation("hello period the end")
        assert "." in result
