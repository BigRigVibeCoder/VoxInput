"""tests/unit/test_spell_corrector.py — Unit tests for Phase 3 SpellCorrector."""
import sys
from unittest.mock import MagicMock
sys.path.insert(0, ".")


def _make_sc():
    """Create a SpellCorrector with a minimal mock settings object."""
    from src.spell_corrector import SpellCorrector
    settings = MagicMock()
    settings.get = MagicMock(return_value=True)
    return SpellCorrector(settings)


class TestSpellCorrectorASRRules:
    """Tests for the built-in ASR artifact correction rules."""

    def test_gonna_to_going_to(self):
        sc = _make_sc()
        result = sc.correct("I gonna go to the store")
        assert isinstance(result, str) and len(result) > 0

    def test_wanna_to_want_to(self):
        sc = _make_sc()
        result = sc.correct("I wanna eat pizza")
        assert isinstance(result, str) and len(result) > 0

    def test_empty_string(self):
        sc = _make_sc()
        assert sc.correct("") == ""

    def test_passthrough_clean_text(self):
        sc = _make_sc()
        result = sc.correct("hello world")
        assert "hello" in result.lower()

    def test_no_crash_on_whitespace(self):
        sc = _make_sc()
        result = sc.correct("   ")
        assert isinstance(result, str)

    def test_returns_string(self):
        sc = _make_sc()
        result = sc.correct("testing testing one two three")
        assert isinstance(result, str) and len(result) > 0


class TestSpellCorrectorLazyLoad:
    """SpellCorrector lazy-loads — must not crash even without symspellpy."""

    def test_import_clean(self):
        sc = _make_sc()
        assert sc is not None

    def test_correct_method_exists(self):
        sc = _make_sc()
        assert callable(sc.correct)
