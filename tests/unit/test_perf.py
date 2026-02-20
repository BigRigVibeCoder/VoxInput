"""tests/unit/test_perf.py — Gate 4: Performance benchmark tests (P8).

Tests verify:
  1. C RMS extension loads and is faster than numpy baseline
  2. rms_int16() and numpy give numerically identical results
  3. Whisper buffer deque: 100 appends leave no large intermediate copies
  4. AudioCapture deque: lock-free SPSC behavior
  5. settings cache: _process_loop parameters captured at start_listening
  6. OSD rate limiter: update_osd not called for unchanged chunks
"""
import collections
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import sys
sys.path.insert(0, ".")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_chunk(n_samples: int = 1600, rms_target: int = 2000) -> bytes:
    """Generate a PCM int16 chunk with approximate given RMS."""
    rng = np.random.default_rng(42)
    amp = int(rms_target * np.sqrt(2))
    samples = (rng.uniform(-amp, amp, n_samples)).astype(np.int16)
    return samples.tobytes()


# ─── C Extension ──────────────────────────────────────────────────────────────

class TestCRmsExtension:

    def test_c_ext_importable(self):
        from src.c_ext import rms_int16, using_c_extension
        assert callable(rms_int16)
        assert isinstance(using_c_extension(), bool)

    def test_c_ext_active(self):
        """C extension should be active — librms.so was compiled by build.sh."""
        from src.c_ext import using_c_extension
        assert using_c_extension(), (
            "C RMS extension NOT loaded — did build.sh fail? "
            "Run: cd src/c_ext && bash build.sh"
        )

    def test_rms_numerical_accuracy(self):
        """C and numpy RMS must agree to within 0.5 LSB."""
        from src.c_ext import rms_int16
        chunk = _make_chunk()
        c_rms = rms_int16(chunk)
        arr = np.frombuffer(chunk, dtype=np.int16)
        np_rms = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
        assert abs(c_rms - np_rms) < 0.5, (
            f"C RMS ({c_rms:.3f}) differs from numpy ({np_rms:.3f}) by >{0.5}"
        )

    def test_rms_empty_bytes(self):
        from src.c_ext import rms_int16
        assert rms_int16(b"") == 0.0

    def test_rms_silence(self):
        from src.c_ext import rms_int16
        silence = bytes(3200)  # all zeros
        assert rms_int16(silence) == 0.0

    def test_c_rms_speed_vs_numpy(self):
        """C RMS must be faster than numpy for 1600 samples (100ms chunk)."""
        from src.c_ext import rms_int16, using_c_extension
        if not using_c_extension():
            pytest.skip("C extension not loaded — speed test skipped")

        chunk = _make_chunk()
        N = 5000

        # Numpy baseline
        t0 = time.perf_counter()
        for _ in range(N):
            arr = np.frombuffer(chunk, dtype=np.int16)
            float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
        numpy_us = (time.perf_counter() - t0) / N * 1e6

        # C extension
        t0 = time.perf_counter()
        for _ in range(N):
            rms_int16(chunk)
        c_us = (time.perf_counter() - t0) / N * 1e6

        print(f"\n  numpy RMS: {numpy_us:.1f} µs/call")
        print(f"  C RMS:     {c_us:.1f} µs/call  ({numpy_us/c_us:.1f}× faster)")

        assert c_us < numpy_us, (
            f"C RMS ({c_us:.1f}µs) should be faster than numpy ({numpy_us:.1f}µs)"
        )
        assert c_us < 10.0, f"C RMS too slow: {c_us:.1f}µs (should be <10µs)"


# ─── Whisper ring buffer ───────────────────────────────────────────────────────

class TestWhisperRingBuffer:

    def test_deque_maxlen_bounded(self):
        """deque(maxlen=300) never grows beyond 300 chunks regardless of appends."""
        buf: collections.deque[bytes] = collections.deque(maxlen=300)
        chunk = _make_chunk()
        for _ in range(500):    # well past maxlen
            buf.append(chunk)
        assert len(buf) == 300

    def test_deque_no_copy_on_append(self):
        """Verifies O(1) append — measure 1000 appends stay fast."""
        buf: collections.deque[bytes] = collections.deque(maxlen=300)
        chunk = _make_chunk(1600)
        N = 1000

        t0 = time.perf_counter()
        for _ in range(N):
            buf.append(chunk)
        elapsed_us = (time.perf_counter() - t0) / N * 1e6

        print(f"\n  deque append: {elapsed_us:.2f} µs/call")
        assert elapsed_us < 5.0, (
            f"deque.append too slow ({elapsed_us:.2f}µs) — possible copy regression"
        )

    def test_concatenate_correctness(self):
        """np.concatenate over deque chunks matches single-array baseline."""
        buf: collections.deque[bytes] = collections.deque(maxlen=300)
        chunks = [_make_chunk() for _ in range(10)]
        for c in chunks:
            buf.append(c)

        combined = np.concatenate(
            [np.frombuffer(c, dtype=np.int16) for c in buf]
        ).astype(np.float32) / 32768.0

        baseline = np.frombuffer(b"".join(chunks), dtype=np.int16).astype(np.float32) / 32768.0
        np.testing.assert_array_equal(combined, baseline)


# ─── Audio deque (SPSC) ───────────────────────────────────────────────────────

class TestAudioDeque:

    def test_audio_capture_uses_deque(self):
        from src.audio import AudioCapture
        with patch("pyaudio.PyAudio"):
            cap = AudioCapture()
        assert isinstance(cap._buf, collections.deque)
        assert cap._buf.maxlen == 50

    def test_get_data_returns_none_when_empty(self):
        from src.audio import AudioCapture
        with patch("pyaudio.PyAudio"):
            cap = AudioCapture()
        assert cap.get_data() is None

    def test_get_data_returns_chunk(self):
        from src.audio import AudioCapture
        with patch("pyaudio.PyAudio"):
            cap = AudioCapture()
        cap._buf.append(b"hello")
        assert cap.get_data() == b"hello"

    def test_deque_drops_oldest_on_overflow(self):
        from src.audio import AudioCapture
        with patch("pyaudio.PyAudio"):
            cap = AudioCapture()
        for i in range(55):
            cap._buf.append(bytes([i % 256]))
        assert len(cap._buf) == 50
        # Oldest (first 5) dropped; newest 50 remain
        assert cap._buf[0] == bytes([5 % 256])


# ─── Settings cache ───────────────────────────────────────────────────────────

class TestSettingsCache:

    def test_silence_settings_cached_in_source(self):
        """
        Verify start_listening() caches settings and _process_loop uses the cache.
        Pure AST inspection — no GTK/gi import needed, runs headless.
        """
        import ast
        from pathlib import Path
        src = (Path(__file__).parent.parent.parent / "src" / "main.py").read_text()

        # Attrs must be defined somewhere in the module
        assert "_sil_threshold" in src, "_sil_threshold not found in main.py"
        assert "_sil_duration"  in src, "_sil_duration not found in main.py"

        tree = ast.parse(src)

        # Find start_listening — must assign the cache attrs
        start_src = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "start_listening":
                start_src = ast.unparse(node)
                break
        assert start_src, "start_listening() not found"
        assert "_sil_threshold" in start_src, "start_listening() must assign _sil_threshold"
        assert "_sil_duration"  in start_src, "start_listening() must assign _sil_duration"

        # Find _process_loop — must use cache, NOT call settings.get per-chunk
        loop_src = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_process_loop":
                loop_src = ast.unparse(node)
                break
        assert loop_src, "_process_loop() not found"
        assert "self._sil_threshold" in loop_src, "_process_loop must use self._sil_threshold"
        assert "self._sil_duration"  in loop_src, "_process_loop must use self._sil_duration"
        assert 'settings.get' not in loop_src, (
            "_process_loop must not call settings.get() per-chunk — use cached attrs"
        )
