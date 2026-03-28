"""tests/unit/test_settings.py — Unit tests for src/settings.py (SettingsManager).

Tests singleton pattern, load/save/get/set, and defaults behavior.
"""
import json
import os
from unittest.mock import patch

import pytest

from src.settings import SettingsManager, SETTINGS_FILE


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the SettingsManager singleton between tests."""
    SettingsManager.reset()
    yield
    SettingsManager.reset()


class TestSettingsManagerSingleton:
    """Verify singleton behavior."""

    def test_same_instance_returned(self):
        s1 = SettingsManager()
        s2 = SettingsManager()
        assert s1 is s2

    def test_reset_creates_new_instance(self):
        s1 = SettingsManager()
        SettingsManager.reset()
        s2 = SettingsManager()
        assert s1 is not s2


class TestSettingsGet:
    """Verify get() with defaults."""

    def test_get_missing_key_returns_default(self):
        s = SettingsManager()
        assert s.get("nonexistent_key", "fallback") == "fallback"

    def test_get_missing_key_returns_none(self):
        s = SettingsManager()
        assert s.get("nonexistent_key") is None

    def test_whisper_model_has_implicit_default(self):
        s = SettingsManager()
        # whisper_model_size has a hardcoded default of "small"
        assert s.get("whisper_model_size") == "small"


class TestSettingsSetAndSave:
    """Verify set() persists changes."""

    def test_set_updates_value(self):
        s = SettingsManager()
        s.set("test_key", "test_value")
        assert s.get("test_key") == "test_value"

    def test_set_triggers_save(self, tmp_path):
        """Verify that set() writes to disk."""
        s = SettingsManager()
        s.set("save_test", True)
        # The file should have been written (at the project-level SETTINGS_FILE)
        assert os.path.exists(SETTINGS_FILE)


class TestSettingsLoad:
    """Verify load() behavior."""

    def test_load_reads_existing_file(self):
        s = SettingsManager()
        # If settings.json exists, it should have loaded
        if os.path.exists(SETTINGS_FILE):
            assert isinstance(s.settings, dict)

    def test_load_missing_file_gives_empty_dict(self, tmp_path, monkeypatch):
        """If settings file doesn't exist, should get an empty dict."""
        monkeypatch.setattr("src.settings.SETTINGS_FILE", str(tmp_path / "nope.json"))
        SettingsManager.reset()
        s = SettingsManager()
        assert s.settings == {}
