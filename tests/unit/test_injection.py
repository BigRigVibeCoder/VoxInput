"""tests/unit/test_injection.py — Phase 4 injection unit tests."""
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


class TestVoicePunctuation:
    """Unit tests for apply_voice_punctuation() — P4-02."""

    def setup_method(self):
        import importlib, src.injection as inj
        importlib.reload(inj)
        self.apply = inj.apply_voice_punctuation

    def test_period(self):
        assert self.apply("hello period") == "hello ."

    def test_comma(self):
        assert self.apply("yes comma I agree") == "yes , I agree"

    def test_new_line(self):
        assert "\n" in self.apply("next new line here")

    def test_new_paragraph(self):
        assert "\n\n" in self.apply("done new paragraph start")

    def test_question_mark(self):
        assert self.apply("what time is it question mark") == "what time is it ?"

    def test_exclamation(self):
        assert self.apply("wow exclamation mark") == "wow !"

    def test_no_command(self):
        text = "the weather is nice today"
        assert self.apply(text) == text

    def test_multiple_commands(self):
        result = self.apply("hello comma how are you question mark")
        assert "," in result and "?" in result

    def test_case_insensitive(self):
        assert self.apply("hello PERIOD") == "hello ."

    def test_open_close_paren(self):
        result = self.apply("see open paren note close paren")
        assert "(" in result and ")" in result


class TestInjectorBackendDetection:
    """Backend auto-selection: ydotool → xdotool → pynput."""

    def _make_injector(self, ydotool_ok=False, ydotoold_ok=False, xdotool_ok=False):
        import src.injection as inj

        def side_effect(cmd, **kw):
            name = cmd[0]
            if "ydotool" in name:
                if not ydotool_ok:
                    raise FileNotFoundError("ydotool not found")
                m = MagicMock(); m.returncode = 0; return m
            if "pgrep" in name:
                m = MagicMock()
                m.returncode = 0 if ydotoold_ok else 1
                return m
            if "xdotool" in name:
                if not xdotool_ok:
                    raise FileNotFoundError("xdotool not found")
                m = MagicMock(); m.returncode = 0; return m
            m = MagicMock(); m.returncode = 1; return m

        with patch("subprocess.run", side_effect=side_effect):
            return inj.TextInjector()

    def test_prefers_ydotool_when_daemon_running(self):
        inj = self._make_injector(ydotool_ok=True, ydotoold_ok=True)
        assert inj._backend == "ydotool"

    def test_falls_back_to_xdotool_no_daemon(self):
        inj = self._make_injector(ydotool_ok=True, ydotoold_ok=False, xdotool_ok=True)
        assert inj._backend == "xdotool"

    def test_falls_back_to_pynput_when_no_tool(self):
        inj = self._make_injector(ydotool_ok=False, ydotoold_ok=False, xdotool_ok=False)
        assert inj._backend == "pynput"
