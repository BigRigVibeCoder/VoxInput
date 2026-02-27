"""
src/c_ext/__init__.py — VoxInput C extension loader
=====================================================
Loads librms.so at import time. Falls back to numpy on any failure.

Usage:
    from src.c_ext import rms_int16
    rms = rms_int16(audio_bytes)   # PCM int16 raw bytes from PyAudio
"""
from __future__ import annotations

import ctypes
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_lib = None
_c_rms = None
_c_pcm = None

_SO_PATH = Path(__file__).parent / "librms.so"


def _load() -> None:
    global _lib, _c_rms, _c_pcm
    if not _SO_PATH.exists():
        logger.debug("c_ext: librms.so not found — using numpy fallback")
        return
    try:
        _lib = ctypes.CDLL(str(_SO_PATH))

        # RMS hook
        _lib.vox_rms_int16.restype  = ctypes.c_double
        _lib.vox_rms_int16.argtypes = [
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_int,
        ]
        _c_rms = _lib.vox_rms_int16

        # Float32 Cast hook
        _lib.vox_pcm_to_float32.restype = None
        _lib.vox_pcm_to_float32.argtypes = [
            ctypes.POINTER(ctypes.c_int16),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int
        ]
        _c_pcm = _lib.vox_pcm_to_float32

        logger.debug("c_ext: librms.so loaded — using C extensions")
    except Exception as e:
        logger.debug("c_ext: librms.so failed to load (%s) — numpy fallback", e)
        _lib = None
        _c_rms = None
        _c_pcm = None


_load()


def rms_int16(data: bytes) -> float:
    """
    Compute RMS of raw int16 PCM bytes.

    Uses C extension (librms.so) if available, otherwise numpy.
    Both paths are numerically identical.

    Args:
        data: Raw bytes from PyAudio callback (int16 PCM, mono).

    Returns:
        RMS value as float (0 – 32767 range).
    """
    if not data:
        return 0.0

    if _c_rms is not None:
        n = len(data) // 2
        ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_int16))
        return _c_rms(ptr, n)

    # numpy fallback
    arr = np.frombuffer(data, dtype=np.int16)
    return float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))


def using_c_extension() -> bool:
    """Return True if C extension is loaded and active."""
    return _c_rms is not None

def pcm_to_float32(chunks: list[bytes] | collections.deque[bytes]) -> np.ndarray:
    """
    Concatenate a list/deque of raw int16 PCM bytes and return a normalized flat float32 numpy array.
    Uses O(1) single-pass C allocation to avoid slicing bottlenecks on the realtime Whisper thread.

    Equivalent to:
        audio_np = np.concatenate([np.frombuffer(c, dtype=np.int16) for c in chunks]).astype(np.float32) / 32768.0
    """
    total_bytes = sum(len(c) for c in chunks)
    n = total_bytes // 2

    if n <= 0:
        return np.zeros(0, dtype=np.float32)

    out_arr = np.zeros(n, dtype=np.float32)

    if _c_pcm is not None:
        # Avoid allocating massive python byte copies, load into contiguous C array
        full_buffer = b"".join(chunks)
        in_ptr = ctypes.cast(full_buffer, ctypes.POINTER(ctypes.c_int16))
        out_ptr = out_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        _c_pcm(in_ptr, out_ptr, n)
        return out_arr

    # Numpy Fallback
    arr = np.frombuffer(b"".join(chunks), dtype=np.int16)
    return arr.astype(np.float32) / 32768.0
