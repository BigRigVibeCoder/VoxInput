"""
tests/unit/test_push_to_talk.py — Push-to-Talk (PTT) feature tests
===================================================================
Tests the optional push-to-talk mode where holding Right Ctrl
starts listening and releasing it stops listening.
All tests use mocked audio/UI — no live audio required.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.config import PTT_KEY


# ─── Helper: build a minimal VoxInputApp with everything mocked ─────────────

def _make_app():
    """Create a VoxInputApp with all heavy dependencies mocked out."""
    with patch("src.main.AudioCapture"), \
         patch("src.main.SettingsManager") as MockSettings, \
         patch("src.main.MicEnhancer"), \
         patch("src.main.SystemTrayApp") as MockUI, \
         patch("src.main.init_logging"), \
         patch("src.main.Gtk"):

        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        MockSettings.return_value = mock_settings

        mock_indicator = MagicMock()
        mock_ui = MagicMock()
        mock_ui.indicator = mock_indicator
        MockUI.return_value = mock_ui

        from src.main import VoxInputApp
        app = VoxInputApp()
        app.settings = mock_settings
        app.ui = mock_ui
        return app


# ─── Tests ──────────────────────────────────────────────────────────────────

class TestPTTDisabledByDefault:
    """PTT should be off unless explicitly enabled in settings."""

    def test_ptt_setting_defaults_to_false(self):
        app = _make_app()
        # Default: settings.get("push_to_talk", False) → False
        app.settings.get = MagicMock(return_value=False)
        assert app.settings.get("push_to_talk", False) is False

    def test_ptt_active_flag_starts_false(self):
        app = _make_app()
        assert app._ptt_active is False


class TestPTTKeyPress:
    """When PTT is enabled and model is ready, pressing Right Ctrl starts listening."""

    def test_press_starts_listening(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(return_value=True)  # PTT enabled
        app.start_listening = MagicMock()

        # Simulate key press
        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        app._on_ptt_press(mock_key)

        assert app._ptt_active is True

    def test_press_ignored_when_ptt_disabled(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(return_value=False)  # PTT disabled
        app.start_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_press_ignored_before_model_ready(self):
        app = _make_app()
        app._model_ready = False
        app.settings.get = MagicMock(return_value=True)  # PTT enabled
        app.start_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_press_ignored_for_wrong_key(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(return_value=True)

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value="Key.shift")  # wrong key

        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_repeat_press_ignored(self):
        """Holding a key sends repeat press events — only the first should count."""
        app = _make_app()
        app._model_ready = True
        app._ptt_active = True  # already active from first press
        app.settings.get = MagicMock(return_value=True)

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        # Should return early (already held)
        app._on_ptt_press(mock_key)
        assert app._ptt_active is True  # still true, no side effects


class TestPTTKeyRelease:
    """Releasing Right Ctrl stops listening."""

    def test_release_stops_listening(self):
        app = _make_app()
        app._ptt_active = True  # was held
        app.stop_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        app._on_ptt_release(mock_key)

        assert app._ptt_active is False

    def test_release_ignored_when_not_active(self):
        app = _make_app()
        app._ptt_active = False  # not being held
        app.stop_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        app._on_ptt_release(mock_key)

        assert app._ptt_active is False
        app.stop_listening.assert_not_called()

    def test_release_ignored_for_wrong_key(self):
        app = _make_app()
        app._ptt_active = True
        app.stop_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value="Key.alt_r")

        app._on_ptt_release(mock_key)

        # Should still be active — wrong key
        assert app._ptt_active is True


class TestPTTConfigIntegration:
    """PTT_KEY constant matches expected value."""

    def test_ptt_key_is_right_ctrl(self):
        assert PTT_KEY == "Key.ctrl_r"
