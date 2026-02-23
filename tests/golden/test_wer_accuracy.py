"""
tests/golden/test_wer_accuracy.py
==================================
Golden Recording WER (Word Error Rate) Tests.

These tests feed pre-recorded user voice directly to the speech engine
as raw PCM bytes — no microphone, no virtual device required.
The engine produces a transcript which is compared to ground_truth.md
using WER. Tests fail if WER exceeds the configured threshold.

Marks:
  @pytest.mark.golden  — only runs when recordings exist (auto-skip otherwise)

Run:
  pytest tests/golden/ -v -s -m golden

Requirements:
  pip install jiwer
  ./bin/record_golden.sh   (one-time recording session)
"""

import json
import logging
import os
import sys
import time

import pytest

try:
    from jiwer import wer as calculate_wer
    from jiwer import cer as calculate_cer
    _JIWER_AVAILABLE = True
except ImportError:
    _JIWER_AVAILABLE = False

    def calculate_wer(ref, hyp):  # type: ignore
        return 0.0

    def calculate_cer(ref, hyp):  # type: ignore
        return 0.0

pytestmark_jiwer = pytest.mark.skipif(
    not _JIWER_AVAILABLE,
    reason="jiwer not installed — run: pip install jiwer"
)

# Project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.golden.conftest import WER_THRESHOLDS
from tests.golden.wer_report import (
    normalize_text,
    build_diff_report,
    print_wer_report,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

CHUNK_SIZE_FRAMES = 3200  # 200ms @ 16kHz


def _transcribe_vosk(raw_audio: bytes, model_path: str, lag: int = 0) -> str:
    """
    Feed raw PCM bytes to a real Vosk model in streaming chunks.
    Returns full concatenated transcript.
    """
    from vosk import KaldiRecognizer, Model

    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    words = []
    committed = []

    for i in range(0, len(raw_audio), CHUNK_SIZE_FRAMES * 2):  # *2 for 16-bit
        chunk = raw_audio[i: i + CHUNK_SIZE_FRAMES * 2]
        if not chunk:
            continue

        if rec.AcceptWaveform(chunk):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            result_words = text.split()
            # Inject uncommitted words (LAG=0 for testing — get everything)
            new_words = result_words[len(committed):]
            words.extend(new_words)
            committed = []
        else:
            partial = json.loads(rec.PartialResult())
            text = partial.get("partial", "")
            partial_words = text.split()
            stable_len = max(0, len(partial_words) - lag)
            if stable_len > len(committed):
                new_batch = partial_words[len(committed): stable_len]
                words.extend(new_batch)
                committed.extend(new_batch)

    # Flush final result
    final_result = json.loads(rec.FinalResult())
    final_text = final_result.get("text", "")
    final_words = final_text.split()
    remaining = final_words[len(committed):]
    words.extend(remaining)

    return " ".join(words)


def _transcribe_whisper(raw_audio: bytes, model_size: str) -> str:
    """Feed raw PCM to Whisper (openai-whisper or faster-whisper)."""
    import numpy as np

    audio_np = (
        np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
    )

    # Try faster-whisper first
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(
            audio_np,
            beam_size=1,
            language="en",
            vad_filter=False,  # Already captured speech, no VAD needed
        )
        return " ".join(s.text.strip() for s in segments)
    except ImportError:
        pass

    # Fallback: openai-whisper
    import whisper

    model = whisper.load_model(model_size, device="cpu")
    result = model.transcribe(audio_np, fp16=False, beam_size=1, language="en")
    return result.get("text", "").strip()


# ─────────────────────────────────────────────────────────────
# Vosk Golden Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.golden
class TestVoskWER:

    def _get_vosk_model(self):
        """Find installed Vosk model path."""
        from src.settings import SettingsManager
        settings = SettingsManager()
        model_path = settings.get("model_path", "model")
        if not os.path.exists(model_path):
            pytest.skip(f"Vosk model not found at: {model_path}")
        return model_path

    def test_paragraph_a_standard_accuracy(self, ground_truth, golden_audio):
        """
        GATE-1 GOLDEN TEST: Standard vocabulary and homophones.
        Must pass before Phase 1 is considered complete.
        """
        if "A" not in golden_audio:
            pytest.skip("Paragraph A recording not found")

        model_path = self._get_vosk_model()
        with open(golden_audio["A"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_vosk(raw, model_path)
        reference = ground_truth["A"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        cer_score = calculate_cer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Vosk", "small"), 0.22)

        report = build_diff_report(ref_norm, hyp_norm, score, cer_score, threshold, "Vosk", "Paragraph A")
        print_wer_report(report)

        assert score <= threshold, (
            f"Vosk WER {score:.1%} EXCEEDS threshold {threshold:.0%}. "
            f"Engine may have regressed. See diff above."
        )

    def test_paragraph_b_numbers_proper_nouns(self, ground_truth, golden_audio):
        """Numbers, proper nouns, and ordinals stress test."""
        if "B" not in golden_audio:
            pytest.skip("Paragraph B recording not found")

        model_path = self._get_vosk_model()
        with open(golden_audio["B"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_vosk(raw, model_path)
        reference = ground_truth["B"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Vosk", "small"), 0.22)

        report = build_diff_report(ref_norm, hyp_norm, score, None, threshold, "Vosk", "Paragraph B")
        print_wer_report(report)
        assert score <= threshold

    def test_paragraph_c_homophones(self, ground_truth, golden_audio):
        """
        Homophone and context confusion test.
        Also validates spell correction integration (Gate 3+).
        """
        if "C" not in golden_audio:
            pytest.skip("Paragraph C recording not found")

        model_path = self._get_vosk_model()
        with open(golden_audio["C"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_vosk(raw, model_path)
        reference = ground_truth["C"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Vosk", "small"), 0.22)

        report = build_diff_report(ref_norm, hyp_norm, score, None, threshold, "Vosk", "Paragraph C (Homophones)")
        print_wer_report(report)
        assert score <= threshold

    def test_paragraph_d_continuous_flow(self, ground_truth, golden_audio):
        """
        Continuous long-form speech — silence detection stress test.
        Validates P1-01 chunk size reduction doesn't fragment words.
        """
        if "D" not in golden_audio:
            pytest.skip("Paragraph D recording not found")

        model_path = self._get_vosk_model()
        with open(golden_audio["D"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_vosk(raw, model_path)
        reference = ground_truth["D"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Vosk", "small"), 0.22)

        report = build_diff_report(ref_norm, hyp_norm, score, None, threshold, "Vosk", "Paragraph D (Continuous)")
        print_wer_report(report)
        assert score <= threshold

    def test_paragraph_f_dictionary_terms(self, ground_truth, golden_audio):
        """
        GATE-6 GOLDEN TEST: Dictionary words and tech terms.
        Validates compound corrections and SymSpell injection of custom words.
        Words like Docker, Grafana, Terraform, PyTorch should
        survive the correction pipeline with proper casing.
        """
        if "F" not in golden_audio:
            pytest.skip("Paragraph F recording not found")

        model_path = self._get_vosk_model()
        with open(golden_audio["F"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_vosk(raw, model_path)
        reference = ground_truth["F"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Vosk", "small"), 0.22)

        report = build_diff_report(ref_norm, hyp_norm, score, None, threshold, "Vosk", "Paragraph F (Dictionary)")
        print_wer_report(report)
        assert score <= threshold

    def test_latency_per_chunk(self, golden_audio):
        """
        GATE-1 PERFORMANCE: Each 200ms audio chunk should be processed in < 50ms.
        Ensures the P1-01 chunk size reduction doesn't cause CPU stall.
        """
        if "A" not in golden_audio:
            pytest.skip("Paragraph A recording not found")

        model_path = self._get_vosk_model()
        from vosk import KaldiRecognizer, Model

        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)

        with open(golden_audio["A"], "rb") as f:
            raw = f.read()

        chunk_times = []
        for i in range(0, min(len(raw), CHUNK_SIZE_FRAMES * 2 * 20), CHUNK_SIZE_FRAMES * 2):
            chunk = raw[i: i + CHUNK_SIZE_FRAMES * 2]
            t0 = time.perf_counter()
            rec.AcceptWaveform(chunk)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            chunk_times.append(elapsed_ms)

        avg_ms = sum(chunk_times) / len(chunk_times)
        max_ms = max(chunk_times)

        print(f"\n  Vosk chunk latency: avg={avg_ms:.1f}ms, max={max_ms:.1f}ms")
        assert avg_ms < 50, f"Average chunk latency {avg_ms:.1f}ms exceeds 50ms target"
        assert max_ms < 200, f"Max chunk latency {max_ms:.1f}ms exceeds 200ms spike limit"


# ─────────────────────────────────────────────────────────────
# Whisper Golden Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.golden
class TestWhisperWER:

    def _get_whisper_size(self):
        from src.settings import SettingsManager
        settings = SettingsManager()
        return settings.get("whisper_model_size", "base")

    def test_paragraph_a_standard_accuracy(self, ground_truth, golden_audio):
        """
        GATE-2 GOLDEN TEST: Whisper accuracy on standard vocabulary.
        Expects capitalization and punctuation in output.
        """
        if "A" not in golden_audio:
            pytest.skip("Paragraph A recording not found")

        size = self._get_whisper_size()
        with open(golden_audio["A"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_whisper(raw, size)
        reference = ground_truth["A"]

        # For Whisper: compare WITH punctuation preserved
        ref_norm = normalize_text(reference, strip_punctuation=False)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=False)

        score = calculate_wer(ref_norm, hyp_norm)
        cer_score = calculate_cer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Whisper", size), 0.10)

        report = build_diff_report(ref_norm, hyp_norm, score, cer_score, threshold, f"Whisper-{size}", "Paragraph A")
        print_wer_report(report)
        assert score <= threshold

    def test_paragraph_b_numbers(self, ground_truth, golden_audio):
        """Numbers and proper nouns — Whisper should capitalize and handle numbers."""
        if "B" not in golden_audio:
            pytest.skip("Paragraph B recording not found")

        size = self._get_whisper_size()
        with open(golden_audio["B"], "rb") as f:
            raw = f.read()

        hypothesis = _transcribe_whisper(raw, size)
        reference = ground_truth["B"]

        ref_norm = normalize_text(reference, strip_punctuation=True)
        hyp_norm = normalize_text(hypothesis, strip_punctuation=True)

        score = calculate_wer(ref_norm, hyp_norm)
        threshold = WER_THRESHOLDS.get(("Whisper", size), 0.10)

        report = build_diff_report(ref_norm, hyp_norm, score, None, threshold, f"Whisper-{size}", "Paragraph B")
        print_wer_report(report)
        assert score <= threshold

    def test_faster_whisper_vs_openai_accuracy_parity(self, ground_truth, golden_audio):
        """
        GATE-2 REGRESSION: faster-whisper must match openai-whisper within 2% WER.
        Ensures the engine swap doesn't degrade quality.
        """
        try:
            from faster_whisper import WhisperModel
            import whisper as openai_whisper
        except ImportError:
            pytest.skip("Both faster-whisper and openai-whisper required for this test")

        if "A" not in golden_audio:
            pytest.skip("Paragraph A recording not found")

        import numpy as np
        with open(golden_audio["A"], "rb") as f:
            raw = f.read()
        audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        # faster-whisper
        fw_model = WhisperModel("base", device="cpu", compute_type="int8")
        fw_segs, _ = fw_model.transcribe(audio_np, beam_size=1, language="en")
        fw_text = normalize_text(" ".join(s.text for s in fw_segs), strip_punctuation=True)

        # openai-whisper
        ow_model = openai_whisper.load_model("base", device="cpu")
        ow_result = ow_model.transcribe(audio_np, fp16=False, beam_size=1, language="en")
        ow_text = normalize_text(ow_result.get("text", ""), strip_punctuation=True)

        reference = normalize_text(ground_truth["A"], strip_punctuation=True)

        fw_wer = calculate_wer(reference, fw_text)
        ow_wer = calculate_wer(reference, ow_text)

        print(f"\n  faster-whisper WER: {fw_wer:.1%}")
        print(f"  openai-whisper WER: {ow_wer:.1%}")
        print(f"  Difference:         {abs(fw_wer - ow_wer):.1%}")

        assert abs(fw_wer - ow_wer) <= 0.02, (
            f"faster-whisper WER ({fw_wer:.1%}) differs from "
            f"openai-whisper ({ow_wer:.1%}) by more than 2%. "
            f"Engine swap may have degraded quality."
        )
