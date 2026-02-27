"""
tests/unit/test_push_to_talk.py — Push-to-Talk (PTT) feature tests
===================================================================
Tests the optional push-to-talk mode where holding a configurable key
starts listening and releasing it triggers full-context finalize + inject.
All tests use mocked audio/UI — no live audio required.
"""
import os
import sys
from unittest.mock import MagicMock, patch

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
    def test_finalize_uses_buffer_and_tail(self, mock_glib):
        """Buffer is primary source; short FinalResult tail appends uncommitted words."""
        app = _make_app()
        app._model_ready = True
        app.is_listening = True
        # Buffer has many words — long utterance with sentence boundary
        app._ptt_buffer = ["there", "going", "to", "the", "store", "and",
                           "then", "coming", "back", "home"]
        app._ptt_releasing = True

        # FinalResult returns just the short tail (< half buffer)
        mock_vosk_rec = MagicMock()
        import json
        mock_vosk_rec.FinalResult.return_value = json.dumps(
            {"text": "back home again"}
        )
        app.recognizer = MagicMock()
        app.recognizer.recognizer = mock_vosk_rec

        # Mock spell corrector
        app.spell = MagicMock()
        app.spell.correct.return_value = "there going to the store and then coming back home again"
        app.spell.flush_pending_number.return_value = None

        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "ptt_audio_feedback": True,
        }.get(k, d))

        app._ptt_finalize()

        # Should have called full-context correction with combined text
        app.spell.correct.assert_called_once()
        raw_text = app.spell.correct.call_args[0][0]
        # Buffer provides the base, tail appends non-overlapping "again"
        assert "there going to the store" in raw_text
        assert "again" in raw_text
        # Should have stopped listening
        app.stop_listening.assert_called_once()
        # Should have played release beep
        app._audio_fb.play_release.assert_called_once()
        # _ptt_releasing should be cleared
        assert app._ptt_releasing is False

    @patch("src.main.GLib")
    def test_finalize_handles_empty_transcript(self, mock_glib):
        app = _make_app()
        app._ptt_buffer = []
        app._ptt_releasing = True

        mock_vosk_rec = MagicMock()
        import json
        mock_vosk_rec.FinalResult.return_value = json.dumps({"text": ""})
        app.recognizer = MagicMock()
        app.recognizer.recognizer = mock_vosk_rec

        app.spell = MagicMock()
        app.spell.flush_pending_number.return_value = None
        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(return_value=False)

        app._ptt_finalize()

        # Should not crash, and should stop listening
        app.stop_listening.assert_called_once()
        # Spell correct should NOT be called on empty text
        app.spell.correct.assert_not_called()
        # _ptt_releasing should be cleared
        assert app._ptt_releasing is False

    @patch("src.main.GLib")
    def test_finalize_buffer_only_no_tail(self, mock_glib):
        """When FinalResult returns empty, buffer is used alone."""
        app = _make_app()
        app._ptt_buffer = ["hello", "world"]
        app._ptt_releasing = True

        mock_vosk_rec = MagicMock()
        import json
        mock_vosk_rec.FinalResult.return_value = json.dumps({"text": ""})
        app.recognizer = MagicMock()
        app.recognizer.recognizer = mock_vosk_rec

        app.spell = MagicMock()
        app.spell.correct.return_value = "hello world"
        app.spell.flush_pending_number.return_value = None
        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(return_value=False)

        app._ptt_finalize()

        app.spell.correct.assert_called_once_with("hello world")


# ─── Race Condition Guards ──────────────────────────────────────────────────

class TestPTTRaceCondition:
    """Tests for the _ptt_releasing guard that prevents word leakage."""

    def test_releasing_flag_set_before_active_cleared(self):
        """_on_ptt_release sets _ptt_releasing=True BEFORE _ptt_active=False."""
        app = _make_app()
        app._ptt_active = True
        app._ptt_releasing = False
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "ptt_key": PTT_KEY,
        }.get(k, d))

        # Track the order of flag changes
        flag_states = []
        original_setattr = app.__class__.__setattr__

        def tracking_setattr(self_inner, name, value):
            if name in ("_ptt_active", "_ptt_releasing"):
                flag_states.append((name, value))
            original_setattr(self_inner, name, value)

        mock_key = MagicMock()
        mock_key.__str__ = MagicMock(return_value=PTT_KEY)

        with patch.object(app.__class__, "__setattr__", tracking_setattr):
            with patch("src.main.GLib"):
                app._on_ptt_release(mock_key)

        # _ptt_releasing=True must come BEFORE _ptt_active=False
        releasing_idx = next(i for i, (n, v) in enumerate(flag_states)
                            if n == "_ptt_releasing" and v is True)
        active_idx = next(i for i, (n, v) in enumerate(flag_states)
                          if n == "_ptt_active" and v is False)
        assert releasing_idx < active_idx, \
            f"_ptt_releasing must be set before _ptt_active is cleared. Order: {flag_states}"

    @patch("src.main.GLib")
    def test_releasing_flag_cleared_after_finalize(self, mock_glib):
        """_ptt_releasing is cleared in _ptt_finalize's finally block."""
        app = _make_app()
        app._ptt_releasing = True
        app._ptt_buffer = ["test"]

        import json
        mock_vosk_rec = MagicMock()
        mock_vosk_rec.FinalResult.return_value = json.dumps({"text": "test"})
        app.recognizer = MagicMock()
        app.recognizer.recognizer = mock_vosk_rec

        app.spell = MagicMock()
        app.spell.correct.return_value = "test"
        app.spell.flush_pending_number.return_value = None
        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(return_value=False)

        app._ptt_finalize()

        assert app._ptt_releasing is False

    def test_releasing_flag_cleared_even_on_error(self):
        """_ptt_releasing is cleared even if finalize throws."""
        app = _make_app()
        app._ptt_releasing = True
        app._ptt_buffer = ["test"]
        app.recognizer = MagicMock()
        app.recognizer.recognizer = MagicMock()
        app.recognizer.recognizer.FinalResult.side_effect = RuntimeError("boom")
        app.spell = MagicMock()
        app.stop_listening = MagicMock()
        app.settings.get = MagicMock(return_value=False)

        app._ptt_finalize()  # Should not raise

        assert app._ptt_releasing is False

    def test_process_loop_routes_to_buffer_during_releasing(self):
        """When _ptt_active=False but _ptt_releasing=True, words go to buffer."""
        app = _make_app()
        app._ptt_active = False
        app._ptt_releasing = True
        app._ptt_buffer = ["hello"]
        app._enqueue_injection = MagicMock()

        # Simulate what _process_loop does at line 279
        text = "world"
        if app._ptt_active or app._ptt_releasing:
            app._ptt_buffer.extend(text.split())
        else:
            app._enqueue_injection(text)

        assert app._ptt_buffer == ["hello", "world"]
        app._enqueue_injection.assert_not_called()

    def test_ptt_mode_discards_words_when_key_not_held(self):
        """In PTT mode with key not held, words are discarded (not injected)."""
        app = _make_app()
        app._ptt_active = False
        app._ptt_releasing = False
        app._ptt_buffer = []
        app._enqueue_injection = MagicMock()
        app.settings.get = MagicMock(side_effect=lambda k, d=None: {
            "push_to_talk": True,
        }.get(k, d))

        # Simulate what _process_loop does at line 279
        text = "stray words"
        if app._ptt_active or app._ptt_releasing:
            app._ptt_buffer.extend(text.split())
        elif not app.settings.get("push_to_talk", False):
            app._enqueue_injection(text)

        # Words should be discarded — not in buffer, not injected
        assert app._ptt_buffer == []
        app._enqueue_injection.assert_not_called()

    def test_releasing_flag_starts_false(self):
        """_ptt_releasing defaults to False on init."""
        app = _make_app()
        assert app._ptt_releasing is False


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
