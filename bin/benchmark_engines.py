#!/usr/bin/env python3
"""
bin/benchmark_engines.py — WER Benchmark: Vosk vs Whisper
==========================================================
Runs each engine against the golden recordings and reports
WER using the normalized comparison (handles Whisper's smart
formatting: punctuation, digits, ordinals).
"""
import json
import os
import re
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests", "e2e"))

from test_golden_e2e import normalize, word_error_rate, parse_ground_truth

ROOT = os.path.join(os.path.dirname(__file__), "..")
WAV = os.path.join(ROOT, "tests", "fixtures", "golden", "recordings", "paragraph_e.wav")

gt = parse_ground_truth()
GROUND_TRUTH = gt.get("E", "")

if not GROUND_TRUTH:
    print("ERROR: No ground truth for Paragraph E")
    sys.exit(1)

print(f"Ground truth (first 100 chars): {normalize(GROUND_TRUTH)[:100]}...")
print(f"WAV: {WAV}")
print()

results = []


def benchmark_vosk():
    """Benchmark Vosk gigaspeech."""
    model_path = os.path.join(ROOT, "model", "gigaspeech")
    if not os.path.isdir(model_path):
        print("  SKIP: gigaspeech model not found")
        return

    from vosk import KaldiRecognizer, Model

    print("=== Vosk gigaspeech ===")
    t0 = time.time()
    m = Model(model_path)
    rec = KaldiRecognizer(m, 16000)
    rec.SetWords(True)

    wf = wave.open(WAV, "rb")
    words = []
    while True:
        data = wf.readframes(4096)
        if not data:
            break
        if rec.AcceptWaveform(data):
            words.append(json.loads(rec.Result()).get("text", ""))
    words.append(json.loads(rec.FinalResult()).get("text", ""))
    wf.close()

    hyp = " ".join(w for w in words if w)
    elapsed = time.time() - t0
    w = word_error_rate(GROUND_TRUTH, hyp)
    print(f"  WER: {w:.1%}  Time: {elapsed:.1f}s")
    print(f"  RAW:  {hyp[:100]}...")
    print(f"  NORM: {normalize(hyp)[:100]}...")
    results.append(("Vosk gigaspeech", w, elapsed))


def benchmark_whisper():
    """Benchmark faster-whisper models."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  SKIP: faster-whisper not installed")
        return

    wf = wave.open(WAV, "rb")
    raw = wf.readframes(wf.getnframes())
    wf.close()
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    for name in ["tiny", "base", "small"]:
        print(f"\n=== faster-whisper {name} ===")
        t0 = time.time()
        try:
            model = WhisperModel(name, device="cuda", compute_type="float16")
            device_used = "GPU"
        except Exception:
            model = WhisperModel(name, device="cpu", compute_type="int8")
            device_used = "CPU"

        segments, _ = model.transcribe(audio, beam_size=1, language="en")
        hyp = " ".join(s.text.strip() for s in segments)
        elapsed = time.time() - t0
        w = word_error_rate(GROUND_TRUTH, hyp)
        print(f"  WER: {w:.1%}  Time: {elapsed:.1f}s  ({device_used})")
        print(f"  RAW:  {hyp[:100]}...")
        print(f"  NORM: {normalize(hyp)[:100]}...")
        results.append((f"Whisper {name} ({device_used})", w, elapsed))
        del model


if __name__ == "__main__":
    benchmark_vosk()
    benchmark_whisper()

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY (Paragraph E)")
    print("=" * 60)
    print(f"{'Engine':<30} {'WER':>6} {'Time':>8}")
    print("-" * 60)
    for name, w, t in sorted(results, key=lambda x: x[1]):
        print(f"{name:<30} {w:>5.1%} {t:>7.1f}s")
    print()
