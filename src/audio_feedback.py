"""
src/audio_feedback.py — Synthesized audio cues for push-to-talk.

Generates two short beep tones at init using pure Python (math + struct):
  - Press beep:   880 Hz, 80ms, ascending (signal: mic is on)
  - Release beep: 440 Hz, 80ms, descending (signal: processing/done)

Plays via aplay (ALSA CLI, always available on Linux) in a non-blocking
subprocess.  Cached as temp WAV files so generation is one-time.

Respects the settings key "ptt_audio_feedback" (default: True).
"""
import logging
import math
import os
import struct
import subprocess
import tempfile
import wave

logger = logging.getLogger(__name__)

# Audio parameters
_SAMPLE_RATE = 22050
_DURATION_MS = 80
_N_SAMPLES = int(_SAMPLE_RATE * _DURATION_MS / 1000)
_AMPLITUDE = 0.35  # soft — not startling


def _generate_tone(freq_start: float, freq_end: float) -> bytes:
    """Generate a linear frequency sweep as 16-bit PCM samples."""
    samples = []
    for i in range(_N_SAMPLES):
        t = i / _SAMPLE_RATE
        # Linear frequency sweep
        progress = i / _N_SAMPLES
        freq = freq_start + (freq_end - freq_start) * progress
        # Fade in/out envelope to avoid click
        envelope = 1.0
        fade_len = _N_SAMPLES // 8
        if i < fade_len:
            envelope = i / fade_len
        elif i > _N_SAMPLES - fade_len:
            envelope = (_N_SAMPLES - i) / fade_len
        value = _AMPLITUDE * envelope * math.sin(2 * math.pi * freq * t)
        samples.append(int(value * 32767))
    return struct.pack(f"<{len(samples)}h", *samples)


def _write_wav(path: str, pcm_data: bytes):
    """Write PCM samples as a WAV file."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm_data)


class AudioFeedback:
    """Plays press/release beeps for push-to-talk."""

    def __init__(self):
        self._press_wav: str | None = None
        self._release_wav: str | None = None
        self._available = False
        try:
            self._init_sounds()
            self._available = True
            logger.info("AudioFeedback ready (aplay)")
        except Exception as e:
            logger.warning(f"AudioFeedback init failed: {e} — beeps disabled")

    def _init_sounds(self):
        """Generate and cache the beep WAV files."""
        tmpdir = tempfile.gettempdir()

        press_path = os.path.join(tmpdir, "voxinput_beep_press.wav")
        release_path = os.path.join(tmpdir, "voxinput_beep_release.wav")

        # Generate only if not already cached
        if not os.path.exists(press_path):
            _write_wav(press_path, _generate_tone(660, 880))  # ascending
        if not os.path.exists(release_path):
            _write_wav(release_path, _generate_tone(880, 440))  # descending

        # Verify aplay is available
        result = subprocess.run(
            ["which", "aplay"], capture_output=True, timeout=2
        )
        if result.returncode != 0:
            raise FileNotFoundError("aplay not found")

        self._press_wav = press_path
        self._release_wav = release_path

    def play_press(self):
        """Play the press (ascending) beep. Non-blocking."""
        if self._available and self._press_wav:
            self._play(self._press_wav)

    def play_release(self):
        """Play the release (descending) beep. Non-blocking."""
        if self._available and self._release_wav:
            self._play(self._release_wav)

    def _play(self, path: str):
        """Play a WAV file via aplay in a fire-and-forget subprocess."""
        try:
            subprocess.Popen(
                ["aplay", "-q", path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logger.debug(f"Beep play failed: {e}")
