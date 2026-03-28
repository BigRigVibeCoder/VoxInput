"""tests/unit/test_audio_feedback.py — Unit tests for src/audio_feedback.py.

Tests WAV generation, beep caching, and play/no-play decision paths
without actuating speakers (mocked subprocess).
"""
import math
import os
import struct
from unittest.mock import MagicMock, patch

import pytest


class TestToneGeneration:
    """Verify the PCM tone generator math."""

    def test_generate_tone_returns_bytes(self):
        from src.audio_feedback import _generate_tone
        pcm = _generate_tone(440, 880)
        assert isinstance(pcm, bytes)
        assert len(pcm) > 0

    def test_generate_tone_length_matches_sample_count(self):
        from src.audio_feedback import _generate_tone, _N_SAMPLES
        pcm = _generate_tone(440, 880)
        # 2 bytes per int16 sample
        assert len(pcm) == _N_SAMPLES * 2

    def test_generate_tone_is_deterministic(self):
        from src.audio_feedback import _generate_tone
        assert _generate_tone(660, 880) == _generate_tone(660, 880)


class TestWriteWav:
    """Verify WAV file writing."""

    def test_write_wav_creates_file(self, tmp_path):
        from src.audio_feedback import _write_wav, _generate_tone
        path = str(tmp_path / "test.wav")
        _write_wav(path, _generate_tone(440, 880))
        assert os.path.exists(path)
        assert os.path.getsize(path) > 44  # WAV header + data


class TestAudioFeedback:
    """Verify AudioFeedback lifecycle."""

    @patch("src.audio_feedback.subprocess.run")
    def test_init_generates_beep_files(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from src.audio_feedback import AudioFeedback
        fb = AudioFeedback()
        assert fb._available is True
        assert fb._press_wav is not None
        assert fb._release_wav is not None

    @patch("src.audio_feedback.subprocess.run")
    def test_init_disabled_if_aplay_missing(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)  # aplay not found
        from src.audio_feedback import AudioFeedback
        fb = AudioFeedback()
        assert fb._available is False

    @patch("src.audio_feedback.subprocess.Popen")
    @patch("src.audio_feedback.subprocess.run")
    def test_play_press_calls_aplay(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(returncode=0)
        from src.audio_feedback import AudioFeedback
        fb = AudioFeedback()
        fb.play_press()
        mock_popen.assert_called_once()
        assert "aplay" in mock_popen.call_args[0][0]

    @patch("src.audio_feedback.subprocess.run")
    def test_play_noop_when_unavailable(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        from src.audio_feedback import AudioFeedback
        fb = AudioFeedback()
        fb.play_press()  # should not raise
        fb.play_release()  # should not raise
