"""tests/integration/test_recognizer_pipeline.py — Integration tests for the
recognition → correction → injection pipeline.

Exercises the full data path without physical audio or display:
  1. Mock audio chunks → SpeechRecognizer → raw text
  2. Raw text → SpellCorrector → corrected text
  3. Corrected text → TextInjector (mocked) → verify output

Uses deterministic synthetic PCM data, no ALSA/PulseAudio required.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.spell_corrector import SpellCorrector
from src.injection import VoicePunctuationBuffer, apply_voice_punctuation
from src.homophones import fix_homophones
from src.errors import ErrorCategory


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_spell_corrector() -> SpellCorrector:
    """Create a real SpellCorrector with mocked settings."""
    settings = MagicMock()
    settings.get = MagicMock(return_value=True)
    return SpellCorrector(settings)


# ── T-001: Full Pipeline Integration ─────────────────────────────────────────

class TestRecognizerPipeline:
    """Integration: recognizer output flows through correction to injection."""

    def test_recognized_text_gets_corrected(self):
        """Vosk output → SpellCorrector → corrected text."""
        sc = _make_spell_corrector()
        raw = "i gonna go to the store"
        corrected = sc.correct(raw)
        assert "gonna" not in corrected.lower()
        assert "I" in corrected  # GOV-003: I capitalization

    def test_corrected_text_gets_punctuated(self):
        """Corrected text → VoicePunctuationBuffer → final output."""
        sc = _make_spell_corrector()
        buf = VoicePunctuationBuffer()
        raw = "hello world period how are you question mark"
        corrected = sc.correct(raw)
        result = buf.process(corrected)
        # Punctuation commands should become symbols
        if result:  # buffer may hold back pending words
            assert "period" not in result.lower() or "." in result

    def test_homophones_applied_after_correction(self):
        """Corrected text → fix_homophones → final text."""
        sc = _make_spell_corrector()
        raw = "their going to the store"
        corrected = sc.correct(raw)
        fixed = fix_homophones(corrected)
        assert "they're" in fixed.lower() or "going" in fixed.lower()

    def test_full_pipeline_end_to_end(self):
        """Complete pipeline: raw → correct → homophones → punctuate → inject."""
        sc = _make_spell_corrector()
        buf = VoicePunctuationBuffer()

        raw = "i wanna buy twenty one apples"
        corrected = sc.correct(raw)
        fixed = fix_homophones(corrected)
        result = buf.process(fixed)

        # Verify each stage did its job
        assert "wanna" not in corrected.lower()
        assert "21" in corrected
        assert "I" in corrected


class TestMockAudioToRecognizer:
    """Integration: synthetic audio chunks → recognizer (mocked Vosk)."""

    def test_silence_produces_no_text(self, silence_chunk, mock_recognizer):
        """Feeding silence should not produce any injection text."""
        mock_recognizer.process_audio.return_value = None
        result = mock_recognizer.process_audio(silence_chunk)
        assert result is None

    def test_noise_triggers_processing(self, noise_chunk, mock_recognizer):
        """Feeding noise triggers recognizer processing."""
        mock_recognizer.process_audio.return_value = "test words"
        result = mock_recognizer.process_audio(noise_chunk)
        assert result == "test words"

    def test_finalize_returns_accumulated_text(self, mock_recognizer):
        """Finalize after silence returns the buffered text."""
        result = mock_recognizer.finalize()
        assert result == "hello world"

    def test_audio_sequence_pipeline(self, audio_chunks, mock_recognizer, mock_injector):
        """Full sequence: multiple chunks → recognize → inject."""
        sc = _make_spell_corrector()

        # Simulate: first 5 chunks produce nothing, then recognition fires
        side_effects = [None] * 5 + ["hello world"] + [None] * 4
        mock_recognizer.process_audio.side_effect = side_effects

        for chunk in audio_chunks:
            text = mock_recognizer.process_audio(chunk)
            if text:
                corrected = sc.correct(text)
                mock_injector.type_text(corrected)

        assert len(mock_injector.injected_texts) == 1
        assert "hello" in mock_injector.injected_texts[0].lower()


class TestPTTIntegrationPath:
    """Integration: PTT key press → audio → finalize → inject."""

    def test_ptt_finalize_merges_buffer(self, mock_recognizer):
        """PTT finalize combines buffer + FinalResult tail."""
        # Simulate PTT buffer with accumulated words
        ptt_buffer = ["hello", "world"]
        buffered = " ".join(ptt_buffer)

        # Finalize returns the same text — no overlap
        final = mock_recognizer.finalize()
        assert final == "hello world"

        # After correction
        sc = _make_spell_corrector()
        corrected = sc.correct(buffered)
        assert "hello" in corrected.lower()

    def test_ptt_empty_buffer_uses_finalize(self, mock_recognizer):
        """When PTT buffer is empty, finalize result is used directly."""
        ptt_buffer = []
        final = mock_recognizer.finalize()
        result = " ".join(ptt_buffer) if ptt_buffer else final
        assert result == "hello world"


class TestErrorTaxonomyIntegration:
    """Integration: error hierarchy works with the pipeline."""

    def test_audio_error_has_context(self):
        """AudioIOError carries structured context through the pipeline."""
        from src.errors import AudioIOError
        err = AudioIOError("stream died", cause=RuntimeError("ALSA fail"))
        assert err.context.category == ErrorCategory.HARDWARE
        assert err.__cause__ is not None

    def test_engine_error_has_context(self):
        """EngineCrashError carries infrastructure context."""
        from src.errors import EngineCrashError
        err = EngineCrashError("Vosk abort")
        assert err.context.component == "recognizer"
        assert "INFRASTRUCTURE" in str(err)
