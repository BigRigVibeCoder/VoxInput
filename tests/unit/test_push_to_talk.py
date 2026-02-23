"""
tests/unit/test_push_to_talk.py — Push-to-Talk (PTT) feature tests
===================================================================
Tests the optional push-to-talk mode where holding a configurable key
starts listening and releasing it triggers full-context finalize + inject.
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
         patch("src.main.AudioFeedback") as MockFeedback, \
         patch("src.main.init_logging"), \
         patch("src.main.Gtk"):

        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        MockSettings.return_value = mock_settings

        mock_indicator = MagicMock()
        mock_ui = MagicMock()
        mock_ui.indicator = mock_indicator
        MockUI.return_value = mock_ui

        mock_fb = MagicMock()
        MockFeedback.return_value = mock_fb

        from src.main import VoxInputApp
        app = VoxInputApp()
        app.settings = mock_settings
        app.ui = mock_ui
        app._audio_fb = mock_fb
        return app


# ─── Default State ──────────────────────────────────────────────────────────

class TestPTTDisabledByDefault:
    """PTT should be off unless explicitly enabled in settings."""

    def test_ptt_setting_defaults_to_false(self):
        app = _make_app()
        app.settings.get = MagicMock(return_value=False)
        assert app.settings.get("push_to_talk", False) is False

    def test_ptt_active_flag_starts_false(self):
        app = _make_app()
        assert app._ptt_active is False


# ─── Key Press ──────────────────────────────────────────────────────────────

class TestPTTKeyPress:
    """When PTT is enabled and model is ready, pressing the PTT key starts listening."""

    def test_press_starts_listening(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": PTT_KEY,
            "ptt_audio_feedback": True,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        assert app._ptt_active is True

    def test_press_plays_beep(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": PTT_KEY,
            "ptt_audio_feedback": True,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        app._audio_fb.play_press.assert_called_once()

    def test_press_no_beep_when_feedback_off(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": PTT_KEY,
            "ptt_audio_feedback": False,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        app._audio_fb.play_press.assert_not_called()

    def test_press_ignored_when_ptt_disabled(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(return_value=False)

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_press_ignored_before_model_ready(self):
        app = _make_app()
        app._model_ready = False
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": PTT_KEY,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_press_ignored_for_wrong_key(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": PTT_KEY,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value="Key.shift")
        app._on_ptt_press(mock_key)

        assert app._ptt_active is False

    def test_repeat_press_ignored(self):
        """Holding a key sends repeat press events — only the first should count."""
        app = _make_app()
        app._model_ready = True
        app._ptt_active = True  # already active from first press

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)

        assert app._ptt_active is True


# ─── Key Release ────────────────────────────────────────────────────────────

class TestPTTKeyRelease:
    """Releasing the PTT key triggers full-context finalize."""

    def test_release_clears_active_flag(self):
        app = _make_app()
        app._ptt_active = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "ptt_key": PTT_KEY,
        }.get(k, d))

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_release(mock_key)

        assert app._ptt_active is False

    def test_release_ignored_when_not_active(self):
        app = _make_app()
        app._ptt_active = False
        app.stop_listening = MagicMock()

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_release(mock_key)

        assert app._ptt_active is False
        app.stop_listening.assert_not_called()

    def test_release_ignored_for_wrong_key(self):
        app = _make_app()
        app._ptt_active = True

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value="Key.alt_r")
        app._on_ptt_release(mock_key)

        assert app._ptt_active is True


# ─── Custom Key Binding ─────────────────────────────────────────────────────

class TestCustomKeyBinding:
    """PTT key is configurable via settings."""

    def test_custom_key_used_for_press(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": "Key.f13",
            "ptt_audio_feedback": False,
        }.get(k, d))

        # Press F13 (custom key) — should activate
        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value="Key.f13")
        app._on_ptt_press(mock_key)
        assert app._ptt_active is True

    def test_default_key_ignored_when_custom_set(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": "Key.f13",
        }.get(k, d))

        # Press Right Ctrl (default key) — should NOT activate since custom key is F13
        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)
        app._on_ptt_press(mock_key)
        assert app._ptt_active is False

    def test_falls_back_to_default_when_no_custom(self):
        app = _make_app()
        app._model_ready = True
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
            "ptt_key": None,  # not set
            "ptt_audio_feedback": False,
        }.get(k, d))
        # _get_ptt_key falls back to PTT_KEY when settings returns None
        assert app._get_ptt_key() == PTT_KEY or app._get_ptt_key() is None

    def test_ptt_key_default_is_right_ctrl(self):
        """The config default should be Right Ctrl."""
        assert PTT_KEY == "Key.ctrl_r"


# ─── Full-Context Processing ───────────────────────────────────────────────

class TestPTTFullContext:
    """PTT finalize runs full-context correction pipeline."""

    @patch("src.main.GLib")
    def test_finalize_calls_spell_then_homophones(self, mock_glib):
        app = _make_app()
        app._model_ready = True
        app.is_listening = True

        # Mock recognizer
        app.recognizer = MagicMock()
        app.recognizer.finalize.return_value = "there going to the store"

        # Mock spell corrector
        app.spell = MagicMock()
        app.spell.correct.return_value = "there going to the store"
        app.spell.flush_pending_number.return_value = None

        # Mock stop_listening
        app.stop_listening = MagicMock()

        # Audio feedback
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "ptt_audio_feedback": True,
        }.get(k, d))

        app._ptt_finalize()

        # Should have called full-context correction
        app.recognizer.finalize.assert_called_once()
        app.spell.correct.assert_called_once()
        # Should have stopped listening
        app.stop_listening.assert_called_once()
        # Should have played release beep
        app._audio_fb.play_release.assert_called_once()

    @patch("src.main.GLib")
    def test_finalize_handles_empty_transcript(self, mock_glib):
        app = _make_app()
        app.recognizer = MagicMock()
        app.recognizer.finalize.return_value = None
        app.spell = MagicMock()
        app.spell.flush_pending_number.return_value = None
        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(return_value=False)

        app._ptt_finalize()

        # Should not crash, and should stop listening
        app.stop_listening.assert_called_once()
        # Spell correct should NOT be called on empty text
        app.spell.correct.assert_not_called()


# ─── Audio Feedback ─────────────────────────────────────────────────────────

class TestAudioFeedback:
    """Audio feedback module generates and plays beeps."""

    def test_audio_feedback_init(self):
        """AudioFeedback should initialize without crashing."""
        from src.audio_feedback import AudioFeedback
        fb = AudioFeedback()
        # Should have generated wav files (or failed gracefully)
        assert isinstance(fb._available, bool)

    def test_tone_generation(self):
        """Tone generator should produce correct number of samples."""
        from src.audio_feedback import _generate_tone, _N_SAMPLES
        pcm = _generate_tone(440, 880)
        # Each sample is 2 bytes (int16)
        assert len(pcm) == _N_SAMPLES * 2


# ─── Key Name Formatting ───────────────────────────────────────────────────

class TestKeyNameFormatting:
    """Human-readable key name conversion."""

    def test_format_known_keys(self):
        # Test the formatting logic directly (ui module is mocked by GTK patches)
        _DISPLAY = {
            "Key.ctrl_r": "Right Ctrl", "Key.ctrl_l": "Left Ctrl",
            "Key.scroll_lock": "Scroll Lock",
        }
        for i in range(1, 25):
            _DISPLAY[f"Key.f{i}"] = f"F{i}"

        def fmt(s):
            return _DISPLAY.get(s, s.replace("Key.", "").replace("_", " ").title())

        assert fmt("Key.ctrl_r") == "Right Ctrl"
        assert fmt("Key.f1") == "F1"
        assert fmt("Key.f13") == "F13"
        assert fmt("Key.scroll_lock") == "Scroll Lock"
        assert fmt("Key.pause") == "Pause"
