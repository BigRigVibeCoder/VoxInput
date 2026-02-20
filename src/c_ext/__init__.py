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

_SO_PATH = Path(__file__).parent / "librms.so"


def _load() -> None:
    global _lib, _c_rms
    if not _SO_PATH.exists():
        logger.debug("c_ext: librms.so not found — using numpy fallback")
        return
    try:
        _lib = ctypes.CDLL(str(_SO_PATH))
        _lib.vox_rms_int16.restype  = ctypes.c_double
        _lib.vox_rms_int16.argtypes = [
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_int,
        ]
        _c_rms = _lib.vox_rms_int16
        logger.debug("c_ext: librms.so loaded — using C RMS")
    except Exception as e:
        logger.debug("c_ext: librms.so failed to load (%s) — numpy fallback", e)
        _lib = None
        _c_rms = None


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
