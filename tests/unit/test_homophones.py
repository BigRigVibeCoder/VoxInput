"""tests/unit/test_homophones.py — Unit tests for src/homophones.py.

Tests context-aware homophone corrections per the rule table.
"""
import pytest

from src.homophones import fix_homophones


class TestTheirThereTheyRe:
    """Test their/there/they're disambiguation."""

    def test_they_are_going(self):
        assert "they're going" in fix_homophones("their going").lower()

    def test_over_there(self):
        result = fix_homophones("over their")
        assert "over there" in result.lower()

    def test_their_things(self):
        result = fix_homophones("there things")
        assert "their things" in result.lower()


class TestToTooTwo:
    """Test to/too/two disambiguation."""

    def test_too_much(self):
        result = fix_homophones("to much")
        assert "too much" in result.lower()

    def test_me_too(self):
        result = fix_homophones("me two")
        assert "me too" in result.lower()

    def test_two_robots(self):
        result = fix_homophones("to robots")
        assert "two robots" in result.lower()


class TestItsItIs:
    """Test its/it's disambiguation."""

    def test_it_is_a(self):
        result = fix_homophones("its a")
        assert "it's a" in result.lower()

    def test_its_own(self):
        result = fix_homophones("it's own")
        assert "its own" in result.lower()


class TestThenThan:
    """Test then/than disambiguation."""

    def test_bigger_than(self):
        result = fix_homophones("bigger then")
        assert "bigger than" in result.lower()


class TestNoOpPassthrough:
    """Verify text without homophone triggers passes through unchanged."""

    def test_plain_text_unchanged(self):
        text = "the quick brown fox jumps over the lazy dog"
        assert fix_homophones(text) == text

    def test_empty_string(self):
        assert fix_homophones("") == ""
