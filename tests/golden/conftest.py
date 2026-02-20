"""
tests/golden/conftest.py
========================
Shared fixtures for the golden recording WER test suite.
Provides:
  - virtual_mic: PulseAudio null-sink + virtual source fixture
  - ground_truth: parsed text per paragraph from ground_truth.md
  - golden_audio: path to a recorded paragraph .raw file
"""

import os
import re
import subprocess
import sys
import pytest

# ── Root conftest.py mocks vosk + pyaudio at module level.
# We restore them inside a session-scoped fixture so it runs
# AFTER all conftest loading is done (at actual test execution time).

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "golden")
RECORDINGS_DIR = os.path.join(FIXTURES_DIR, "recordings")
GROUND_TRUTH_FILE = os.path.join(FIXTURES_DIR, "ground_truth.md")

WER_THRESHOLDS = {
    # (engine, model_hint): max_wer
    ("Vosk", "small"):           0.22,
    ("Vosk", "large"):           0.10,
    ("Vosk", "gigaspeech"):      0.08,
    ("Whisper", "tiny"):         0.15,
    ("Whisper", "base"):         0.08,
    ("Whisper", "small"):        0.05,
    ("Whisper", "medium"):       0.03,
    ("faster-whisper", "base"):  0.08,
    ("faster-whisper", "turbo"): 0.03,
}


# ─────────────────────────────────────────────────────────────
# Ground Truth Parser
# ─────────────────────────────────────────────────────────────

def _parse_ground_truth(path: str) -> dict[str, str]:
    """
    Extract the text for each paragraph (A, B, C, D) from ground_truth.md.
    Returns: {"A": "full text...", "B": "full text...", ...}
    """
    paragraphs = {}
    current_label = None
    current_lines = []

    with open(path) as f:
        for line in f:
            line = line.rstrip()

            # Detect paragraph headers: "## Paragraph A — ..."
            m = re.match(r"^## Paragraph ([A-D])", line)
            if m:
                if current_label:
                    paragraphs[current_label] = " ".join(current_lines).strip()
                current_label = m.group(1)
                current_lines = []
                continue

            # Stop at the WER thresholds section
            if "## WER Acceptance" in line or "## Testing Paragraphs" in line:
                break

            # Accumulate non-empty, non-header lines
            if current_label and line and not line.startswith("#"):
                current_lines.append(line.strip())

    # Flush last paragraph
    if current_label and current_lines:
        paragraphs[current_label] = " ".join(current_lines).strip()

    return paragraphs


@pytest.fixture(scope="session", autouse=True)
def restore_real_vosk():
    """
    Remove the MagicMock for vosk/pyaudio that root conftest.py injects.
    Golden tests require the REAL vosk for actual speech transcription.
    This fixture runs at session-start, after all conftests are loaded.
    """
    for _mod in ("vosk", "pyaudio"):
        if _mod in sys.modules and type(sys.modules[_mod]).__name__ == "MagicMock":
            del sys.modules[_mod]
    yield


@pytest.fixture(scope="session")
def ground_truth() -> dict[str, str]:
    """Returns parsed ground truth text by paragraph label."""
    if not os.path.exists(GROUND_TRUTH_FILE):
        pytest.skip(f"Ground truth file not found: {GROUND_TRUTH_FILE}")
    return _parse_ground_truth(GROUND_TRUTH_FILE)


@pytest.fixture(scope="session")
def golden_audio():
    """
    Returns a dict mapping paragraph label → path to .raw PCM file.
    Skips if recordings don't exist.
    """
    files = {}
    for label in ["A", "B", "C", "D"]:
        raw_path = os.path.join(RECORDINGS_DIR, f"paragraph_{label.lower()}.raw")
        if os.path.exists(raw_path):
            files[label] = raw_path

    if not files:
        pytest.skip(
            "No golden recordings found. "
            "Run: ./bin/record_golden.sh"
        )
    return files


# ─────────────────────────────────────────────────────────────
# Virtual Microphone Fixture (for live-stream tests only)
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def virtual_mic():
    """
    Creates a PulseAudio null sink + virtual source for testing.
    VoxInput can be pointed at 'VoxGoldenMic' as if it were a real microphone.
    Audio is injected by playing files to 'VoxGoldenSink'.

    Usage in test:
        subprocess.run(["paplay", "--device=VoxGoldenSink", "file.wav"])
    """
    try:
        r1 = subprocess.run(
            ["pactl", "load-module", "module-null-sink",
             "sink_name=VoxGoldenSink",
             "sink_properties=device.description=VoxGoldenSink"],
            capture_output=True, text=True, check=True, timeout=5
        )
        sink_mod_id = r1.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("PulseAudio not available — virtual mic fixture skipped")
        return

    try:
        r2 = subprocess.run(
            ["pactl", "load-module", "module-virtual-source",
             "source_name=VoxGoldenMic",
             "master=VoxGoldenSink.monitor",
             "source_properties=device.description='VoxInput Golden Mic'"],
            capture_output=True, text=True, check=True, timeout=5
        )
        src_mod_id = r2.stdout.strip()
    except subprocess.CalledProcessError:
        subprocess.run(["pactl", "unload-module", sink_mod_id], check=False)
        pytest.skip("Failed to create virtual source — skipping")
        return

    yield "VoxGoldenMic"

    # Teardown
    subprocess.run(["pactl", "unload-module", src_mod_id], check=False, timeout=5)
    subprocess.run(["pactl", "unload-module", sink_mod_id], check=False, timeout=5)
