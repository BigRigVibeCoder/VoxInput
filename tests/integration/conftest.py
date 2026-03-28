"""tests/integration/conftest.py — Integration test fixtures.

Provides synthetic audio chunks and mock components for integration tests
that exercise the recognizer→spell→injection pipeline without hardware.
"""
import struct
import sys
from unittest.mock import MagicMock

import pytest


def _generate_silence_chunk(num_samples: int = 2048) -> bytes:
    """Generate a chunk of 16-bit PCM silence (all zeros)."""
    return struct.pack(f"<{num_samples}h", *([0] * num_samples))


def _generate_noise_chunk(num_samples: int = 2048, amplitude: int = 100) -> bytes:
    """Generate a chunk of low-amplitude noise for RMS testing."""
    import random
    random.seed(42)  # deterministic
    samples = [random.randint(-amplitude, amplitude) for _ in range(num_samples)]
    return struct.pack(f"<{num_samples}h", *samples)


@pytest.fixture
def silence_chunk() -> bytes:
    """A single chunk of 16-bit PCM silence (2048 samples = 128ms @ 16kHz)."""
    return _generate_silence_chunk()


@pytest.fixture
def noise_chunk() -> bytes:
    """A single chunk of low-amplitude noise for RMS > 0 testing."""
    return _generate_noise_chunk()


@pytest.fixture
def audio_chunks() -> list[bytes]:
    """A sequence of 10 audio chunks simulating a short recording session."""
    return [_generate_noise_chunk(2048, amplitude=50 + i * 30) for i in range(10)]


@pytest.fixture
def mock_recognizer():
    """A mock SpeechRecognizer that returns predetermined text."""
    recognizer = MagicMock()
    recognizer.engine_type = "Vosk"
    recognizer.process_audio = MagicMock(return_value=None)
    recognizer.reset_state = MagicMock()
    recognizer.reset_recognizer = MagicMock()
    recognizer.finalize = MagicMock(return_value="hello world")
    return recognizer


@pytest.fixture
def mock_injector():
    """A mock TextInjector that records injected text."""
    injector = MagicMock()
    injector.injected_texts = []

    def _record(text: str) -> None:
        injector.injected_texts.append(text)

    injector.type_text = MagicMock(side_effect=_record)
    return injector
