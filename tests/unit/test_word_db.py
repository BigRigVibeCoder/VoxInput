"""tests/unit/test_word_db.py — Unit tests for src/word_db.py (WordDatabase).

Tests CRUD operations, compound corrections, seeding, and reloading
using a temporary in-memory database.
"""
import os

import pytest

from src.word_db import WordDatabase


@pytest.fixture
def db(tmp_path):
    """Create a fresh WordDatabase in a temp directory."""
    return WordDatabase(tmp_path / "test_words.db")


class TestWordDatabaseInit:
    """Verify database initialization."""

    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "init_test.db"
        WordDatabase(db_path)
        assert db_path.exists()

    def test_starts_with_compound_corrections(self, db):
        # Default compounds are seeded on first run
        compounds = db.get_compound_corrections()
        assert len(compounds) > 0

    def test_count_starts_at_zero_words(self, db):
        # Words table starts empty (compounds are separate)
        assert db.count() == 0


class TestWordCRUD:
    """Verify word add/remove/lookup."""

    def test_add_word(self, db):
        assert db.add_word("Kubernetes") is True
        assert db.is_protected("kubernetes")
        assert db.is_protected("KUBERNETES")  # case-insensitive

    def test_add_duplicate_returns_false(self, db):
        db.add_word("Docker")
        assert db.add_word("Docker") is False

    def test_remove_word(self, db):
        db.add_word("Terraform")
        assert db.remove_word("terraform") is True
        assert db.is_protected("Terraform") is False

    def test_remove_nonexistent_returns_false(self, db):
        assert db.remove_word("nope") is False

    def test_get_original_case(self, db):
        db.add_word("PyTorch")
        assert db.get_original_case("pytorch") == "PyTorch"

    def test_get_original_case_missing(self, db):
        assert db.get_original_case("missing") is None

    def test_add_empty_string_returns_false(self, db):
        assert db.add_word("") is False
        assert db.add_word("   ") is False


class TestSeed:
    """Verify bulk seeding."""

    def test_seed_populates_words(self, db):
        db.seed([("Python", "language"), ("Rust", "language")])
        assert db.count() == 2
        assert db.is_protected("python")
        assert db.is_protected("rust")

    def test_seed_skips_if_not_empty(self, db):
        db.seed([("Python", "language")])
        db.seed([("Java", "language"), ("Go", "language")])
        # Second seed should be skipped
        assert db.count() == 1


class TestCompoundCorrections:
    """Verify compound correction CRUD."""

    def test_add_compound(self, db):
        assert db.add_compound_correction("fuzzy wuzzy", "FuzzyWuzzy") is True
        compounds = db.get_compound_corrections()
        assert ("fuzzy", "wuzzy") in compounds

    def test_add_duplicate_compound(self, db):
        db.add_compound_correction("pie torch", "PyTorch")
        assert db.add_compound_correction("pie torch", "PyTorch") is False

    def test_remove_compound(self, db):
        db.add_compound_correction("engine next", "nginx")
        assert db.remove_compound_correction("engine next") is True
        assert ("engine", "next") not in db.get_compound_corrections()


class TestGetAll:
    """Verify listing for UI display."""

    def test_get_all_returns_tuples(self, db):
        db.add_word("test_word", "testing")
        results = db.get_all()
        assert len(results) >= 1
        # Each result is (id, word, category, added_at)
        assert results[0][1] == "test_word"

    def test_get_all_with_filter(self, db):
        db.add_word("alpha", "greek")
        db.add_word("beta", "greek")
        db.add_word("gamma", "greek")
        results = db.get_all(filter_text="beta")
        assert len(results) == 1


class TestReload:
    """Verify hot-reload from disk."""

    def test_reload_refreshes_memory(self, db):
        db.add_word("before_reload")
        # Simulate external DB modification by using raw SQL
        db._conn.execute(
            "INSERT INTO words(word, category) VALUES('external_add', 'test')"
        )
        db._conn.commit()
        db.reload()
        assert db.is_protected("external_add")


class TestClose:
    """Verify clean shutdown."""

    def test_close_does_not_raise(self, db):
        db.close()  # should complete without error
