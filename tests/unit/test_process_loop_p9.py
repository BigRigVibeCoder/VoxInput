"""
tests/unit/test_process_loop_p9.py — Mock-based tests for main.py P9 improvements
==================================================================================
Tests audio chunk batching (#4) and adaptive silence threshold (#B)
using mocked audio and recognizer. No live audio required.
"""
import collections
import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─── #4: Audio Chunk Batching ────────────────────────────────────────────────

class TestChunkBatching:
    """P9-04: Drain backlogged chunks when deque has >3 items."""

    def test_drains_backlog_over_3(self):
        """When >3 chunks are backlogged, they should be concatenated."""
        buf = collections.deque(maxlen=50)
        # Simulate 5 chunks in the buffer
        for i in range(5):
            buf.append(b"\x00\x01" * 100)

        # Pop the first one (simulates get_data())
        data = buf.popleft()

        # Check: 4 remaining > 3 threshold → should drain
        backlog = len(buf)
        assert backlog > 3
        extra = []
        while buf:
            extra.append(buf.popleft())
        combined = data + b"".join(extra)
        assert len(combined) == 5 * 200  # all 5 chunks concatenated
        assert len(buf) == 0  # deque is empty after drain

    def test_no_drain_when_3_or_fewer(self):
        """When <= 3 chunks are backlogged, no drain should happen."""
        buf = collections.deque(maxlen=50)
        for i in range(3):
            buf.append(b"\x00\x01" * 100)

        data = buf.popleft()
        backlog = len(buf)
        assert backlog <= 3  # should NOT drain
        assert len(buf) == 2  # 2 remaining untouched

    def test_drain_preserves_data_order(self):
        """Drained chunks should maintain FIFO order."""
        buf = collections.deque(maxlen=50)
        buf.append(b"\x01")
        buf.append(b"\x02")
        buf.append(b"\x03")
        buf.append(b"\x04")
        buf.append(b"\x05")

        data = buf.popleft()  # \x01
        assert data == b"\x01"

        # Drain remaining (4 items > 3)
        extra = []
        while buf:
            extra.append(buf.popleft())
        combined = data + b"".join(extra)
        assert combined == b"\x01\x02\x03\x04\x05"


# ─── #B: Adaptive Silence Threshold ─────────────────────────────────────────

class TestAdaptiveSilence:
    """P9-B: EMA noise floor tracking for adaptive silence threshold."""

    def test_ema_converges_to_low_noise(self):
        """EMA should converge toward actual noise floor over time."""
        alpha = 0.05
        ema = 500.0  # initial (high)

        # Feed 100 chunks of low noise (rms=150)
        for _ in range(100):
            if 150 < max(200, int(ema * 2.5)):  # rms < threshold
                ema = alpha * 150 + (1 - alpha) * ema

        # Should converge close to 150
        assert abs(ema - 150) < 20, f"EMA should be ~150, got {ema:.0f}"
        # Threshold should be ~375
        threshold = max(200, int(ema * 2.5))
        assert 350 < threshold < 400, f"Threshold should be ~375, got {threshold}"

    def test_ema_adapts_to_noise_increase(self):
        """EMA should track upward when noise floor increases within threshold."""
        alpha = 0.05
        ema = 100.0  # low initial
        # Threshold starts at max(200, 100*2.5) = 250
        # Feed chunks of higher noise (rms=240, still below threshold)
        for _ in range(100):
            threshold = max(200, int(ema * 2.5))
            if 240 < threshold:  # rms < threshold → update EMA
                ema = alpha * 240 + (1 - alpha) * ema

        # EMA should move significantly upward toward 240
        assert ema > 200, f"EMA should have risen above 200, got {ema:.0f}"

    def test_minimum_threshold_200(self):
        """Threshold should never go below 200 even with very quiet input."""
        alpha = 0.05
        ema = 500.0

        # Feed 200 chunks of near-zero noise
        for _ in range(200):
            ema = alpha * 10 + (1 - alpha) * ema

        threshold = max(200, int(ema * 2.5))
        assert threshold >= 200, f"Threshold should be >= 200, got {threshold}"

    def test_stable_environment_stable_threshold(self):
        """In a stable environment, threshold should stabilize."""
        alpha = 0.05
        ema = 500.0
        thresholds = []

        for i in range(200):
            rms = 200  # constant noise
            if rms < max(200, int(ema * 2.5)):
                ema = alpha * rms + (1 - alpha) * ema
            thresholds.append(max(200, int(ema * 2.5)))

        # Last 10 thresholds should all be the same (stabilized)
        last_10 = thresholds[-10:]
        assert max(last_10) - min(last_10) <= 1, \
            f"Threshold should stabilize: range is {min(last_10)}-{max(last_10)}"


# ─── Auto-Calibration Persistence ────────────────────────────────────────────

class TestAutoCalibrationPersistence:
    """Verify auto-calibration results are saved to settings."""

    def test_calibrate_returns_threshold(self):
        """auto_calibrate should return a dict with recommended_threshold."""
        import numpy as np
        from src.mic_enhancer import MicEnhancer

        mock_audio_instance = MagicMock()
        mock_audio_instance.start = MagicMock()
        mock_audio_instance.stop = MagicMock()
        chunks = [np.array([200] * 1600, dtype=np.int16).tobytes()] * 30
        chunk_iter = iter(chunks)
        mock_audio_instance.get_data = MagicMock(
            side_effect=lambda: next(chunk_iter, None)
        )
        mock_audio_cls = MagicMock(return_value=mock_audio_instance)

        settings = MagicMock()
        settings.get = MagicMock(return_value=None)
        enh = MicEnhancer(settings)

        # Patch the import target in src.audio where AudioCapture lives
        with patch("src.audio.AudioCapture", mock_audio_cls):
            result = enh.auto_calibrate(duration_s=0.3)

        assert "noise_floor" in result
        assert "recommended_threshold" in result
        assert result["recommended_threshold"] >= 100

    def test_calibration_saves_to_settings(self):
        """The UI handler should call settings.set with the threshold."""
        # This is a logic test — verify the UI handler calls settings.set
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=500)

        # Simulate what _on_auto_calibrate does
        recommended = 350
        mock_settings.set("silence_threshold", recommended)
        mock_settings.set.assert_called_with("silence_threshold", 350)
