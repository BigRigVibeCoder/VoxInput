"""tests/unit/test_audio.py — Unit tests for src/audio.py (AudioCapture).

Tests the deque-based audio buffer, stream lifecycle, and callback behavior
without requiring real audio hardware (mocked PyAudio).
"""
import collections
from unittest.mock import MagicMock, patch

import pytest


class TestAudioCaptureInit:
    """Verify AudioCapture initializes correctly."""

    @patch("src.audio.pyaudio.PyAudio")
    def test_init_creates_deque_buffer(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        assert isinstance(cap._buf, collections.deque)
        assert cap._buf.maxlen == 50
        assert cap.is_running is False
        assert cap.stream is None

    @patch("src.audio.pyaudio.PyAudio")
    def test_init_creates_pyaudio_instance(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        mock_pa.assert_called_once()


class TestAudioCaptureBuffer:
    """Verify the lock-free deque buffer behavior."""

    @patch("src.audio.pyaudio.PyAudio")
    def test_callback_appends_to_buffer(self, mock_pa):
        from src.audio import AudioCapture
        import pyaudio
        cap = AudioCapture()
        cap.is_running = True
        result = cap._callback(b"\x00\x01", 160, {}, 0)
        assert len(cap._buf) == 1
        assert cap._buf[0] == b"\x00\x01"
        assert result == (None, pyaudio.paContinue)

    @patch("src.audio.pyaudio.PyAudio")
    def test_callback_ignores_when_not_running(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        cap.is_running = False
        cap._callback(b"\x00\x01", 160, {}, 0)
        assert len(cap._buf) == 0

    @patch("src.audio.pyaudio.PyAudio")
    def test_get_data_returns_none_when_empty(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        assert cap.get_data() is None

    @patch("src.audio.pyaudio.PyAudio")
    def test_get_data_returns_oldest_chunk(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        cap._buf.append(b"chunk1")
        cap._buf.append(b"chunk2")
        assert cap.get_data() == b"chunk1"
        assert cap.get_data() == b"chunk2"
        assert cap.get_data() is None


class TestAudioCaptureLifecycle:
    """Verify start/stop lifecycle."""

    @patch("src.audio.pyaudio.PyAudio")
    def test_stop_clears_stream(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        mock_stream = MagicMock()
        cap.stream = mock_stream
        cap.is_running = True
        cap.stop()
        assert cap.is_running is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        assert cap.stream is None

    @patch("src.audio.pyaudio.PyAudio")
    def test_stop_noop_without_stream(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        cap.stop()  # should not raise

    @patch("src.audio.pyaudio.PyAudio")
    def test_terminate_calls_pa_terminate(self, mock_pa):
        from src.audio import AudioCapture
        cap = AudioCapture()
        cap.terminate()
        cap.pa.terminate.assert_called_once()
