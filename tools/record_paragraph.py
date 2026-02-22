#!/usr/bin/env python3
"""
tools/record_paragraph.py — Record a benchmark paragraph for WER testing.

Usage:
    python tools/record_paragraph.py

This script:
  1. Displays a paragraph of dictionary words for you to read aloud
  2. Press ENTER to start recording, press ENTER again to stop
  3. Saves the recording as assets/benchmark_paragraph.wav
  4. Prints the reference transcript for WER testing

The paragraph uses common dictionary words covering diverse phonemes,
numbers, homophones, and punctuation-triggering phrases.
"""
import os
import sys
import time
import wave
import struct

# Reference paragraph — common words covering diverse phonemes
REFERENCE_PARAGRAPH = (
    "The quick brown fox jumps over the lazy dog near the river. "
    "She bought twenty three apples and forty seven oranges from the market. "
    "Yesterday afternoon we walked through the beautiful garden together. "
    "Their house is bigger than the one we looked at before. "
    "Please remember to bring your notebook and a pencil to the meeting. "
    "The temperature outside was about sixty five degrees this morning. "
    "Scientists discovered a new species of butterfly in the forest. "
    "He asked whether the project would be finished by next Friday. "
    "My grandmother always said that patience is a great virtue. "
    "The children played happily in the park until the sun went down."
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "benchmark_paragraph.wav")
REFERENCE_PATH = os.path.join(OUTPUT_DIR, "benchmark_paragraph.txt")

RATE = 16000
CHANNELS = 1
FORMAT_WIDTH = 2  # 16-bit


def main():
    try:
        import pyaudio
    except ImportError:
        print("ERROR: pyaudio not installed. Run: pip install pyaudio")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("BENCHMARK PARAGRAPH RECORDING")
    print("=" * 70)
    print()
    print("Read the following paragraph aloud at a natural pace:")
    print()
    print("-" * 70)
    # Print paragraph wrapped at 70 chars
    words = REFERENCE_PARAGRAPH.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > 68:
            print(f"  {line}")
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        print(f"  {line}")
    print("-" * 70)
    print()
    input("Press ENTER to START recording...")

    pa = pyaudio.PyAudio()
    frames = []

    def callback(in_data, frame_count, time_info, status):
        frames.append(in_data)
        return (None, pyaudio.paContinue)

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=1024,
        stream_callback=callback,
    )

    print("🔴 RECORDING... (press ENTER to stop)")
    input()

    stream.stop_stream()
    stream.close()
    pa.terminate()

    # Save WAV
    with wave.open(OUTPUT_PATH, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(FORMAT_WIDTH)
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    duration = len(b"".join(frames)) / (RATE * FORMAT_WIDTH * CHANNELS)

    # Save reference transcript
    with open(REFERENCE_PATH, "w") as f:
        f.write(REFERENCE_PARAGRAPH.strip())

    print()
    print(f"✅ Saved recording: {OUTPUT_PATH}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Reference: {REFERENCE_PATH}")
    print()
    print("Run WER test with:")
    print(f"  python tools/wer_test.py {OUTPUT_PATH} {REFERENCE_PATH}")


if __name__ == "__main__":
    main()
