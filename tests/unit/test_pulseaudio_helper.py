"""tests/unit/test_pulseaudio_helper.py — Unit tests for src/pulseaudio_helper.py.

Tests PulseAudio device parsing and filtering using mocked subprocess output.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.pulseaudio_helper import (
    PulseAudioDevice,
    filter_input_sources,
    get_pulseaudio_sources,
    get_default_source,
    set_default_source,
)


# Realistic pactl output for testing
_PACTL_OUTPUT = """Source #0
\tName: alsa_output.pci-0000_00_1b.0.analog-stereo.monitor
\tDescription: Monitor of Built-in Audio Analog Stereo

Source #1
\tName: alsa_input.usb-Logi_USB_Headset-00.mono-fallback
\tDescription: Logi USB Headset Mono

Source #2
\tName: easyeffects_source
\tDescription: Easy Effects Source
"""


class TestGetPulseAudioSources:
    """Verify pactl output parsing."""

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_parses_three_sources(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=_PACTL_OUTPUT
        )
        sources = get_pulseaudio_sources()
        assert len(sources) == 3
        assert sources[0].name == "alsa_output.pci-0000_00_1b.0.analog-stereo.monitor"
        assert sources[1].name == "alsa_input.usb-Logi_USB_Headset-00.mono-fallback"
        assert sources[2].name == "easyeffects_source"

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_empty_on_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("pactl", 5)
        assert get_pulseaudio_sources() == []

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_empty_on_error(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "pactl")
        assert get_pulseaudio_sources() == []


class TestFilterInputSources:
    """Verify monitor device exclusion."""

    def test_excludes_monitors(self):
        sources = [
            PulseAudioDevice("alsa_out.monitor", "Monitor of Speakers"),
            PulseAudioDevice("alsa_input.usb", "USB Microphone"),
        ]
        result = filter_input_sources(sources)
        assert len(result) == 1
        assert result[0].name == "alsa_input.usb"

    def test_keeps_all_inputs(self):
        sources = [
            PulseAudioDevice("mic1", "Microphone 1"),
            PulseAudioDevice("mic2", "Microphone 2"),
        ]
        assert len(filter_input_sources(sources)) == 2


class TestSetDefaultSource:
    """Verify set_default_source."""

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_true_on_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert set_default_source("test_source") is True

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_false_on_failure(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "pactl")
        assert set_default_source("bad_source") is False


class TestGetDefaultSource:
    """Verify get_default_source."""

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_source_name(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="alsa_input.usb\n"
        )
        assert get_default_source() == "alsa_input.usb"

    @patch("src.pulseaudio_helper.subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "pactl")
        assert get_default_source() is None


class TestPulseAudioDeviceRepr:
    """Verify device repr for debugging."""

    def test_repr_format(self):
        d = PulseAudioDevice("test", "Test Device", 5)
        r = repr(d)
        assert "test" in r
        assert "Test Device" in r
        assert "5" in r
