"""
tests/unit/test_recognizer_p9.py — Mock-based tests for recognizer.py P9 improvements
======================================================================================
Tests Vosk confidence filtering (#2) and partial result caching (#6)
using mocked KaldiRecognizer. No live audio or model required.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_recognizer():
    """Create a SpeechRecognizer with mocked Vosk model and settings."""
    with patch("src.recognizer.Model"), \
         patch("src.recognizer.KaldiRecognizer"):
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(side_effect=lambda key, default=None: {
            "speech_engine": "Vosk",
            "model_path": "/fake/model",
            "fast_mode": False,
            "stability_lag": 2,
            "confidence_threshold": 0.3,
        }.get(key, default))

        with patch("src.recognizer.SpeechRecognizer.__init__", return_value=None):
            from src.recognizer import SpeechRecognizer
            rec = SpeechRecognizer.__new__(SpeechRecognizer)
            rec.settings = mock_settings
            rec.engine_type = "Vosk"
            rec.model = MagicMock()
            rec.recognizer = MagicMock()
            rec.committed_text = []
            rec._last_partial_count = 0
            # Whisper attributes (unused but needed)
            rec.whisper_chunks = []
            rec.whisper_last_transcript = ""
            return rec


def _fake_audio(n_samples=1600):
    """Create fake PCM audio bytes."""
    import struct
    return struct.pack(f"<{n_samples}h", *([1000] * n_samples))


# ─── #2: Confidence Filtering ───────────────────────────────────────────────

class TestConfidenceFiltering:
    """P9-02: Vosk word confidence filtering."""

    def test_full_result_filters_low_confidence(self):
        """Words with conf < 0.3 should be dropped from full results."""
        rec = _make_recognizer()
        # Mock AcceptWaveform returning True (full result)
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "hello um world",
            "result": [
                {"word": "hello", "conf": 0.95, "start": 0.0, "end": 0.5},
                {"word": "um",    "conf": 0.12, "start": 0.5, "end": 0.7},
                {"word": "world", "conf": 0.88, "start": 0.7, "end": 1.2},
            ]
        })

        result = rec._process_vosk(_fake_audio())
        assert result is not None
        assert "hello" in result
        assert "world" in result
        assert "um" not in result

    def test_full_result_keeps_high_confidence(self):
        """All words with conf >= 0.3 should be kept."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "the quick brown fox",
            "result": [
                {"word": "the",   "conf": 0.99, "start": 0.0, "end": 0.2},
                {"word": "quick", "conf": 0.85, "start": 0.2, "end": 0.5},
                {"word": "brown", "conf": 0.92, "start": 0.5, "end": 0.8},
                {"word": "fox",   "conf": 0.78, "start": 0.8, "end": 1.0},
            ]
        })

        result = rec._process_vosk(_fake_audio())
        assert result == "the quick brown fox"

    def test_full_result_no_result_array_uses_text(self):
        """If Vosk doesn't provide 'result' array, fall back to 'text'."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "hello world"
        })

        result = rec._process_vosk(_fake_audio())
        assert result == "hello world"

    def test_all_words_below_threshold_returns_empty(self):
        """If ALL words are below confidence, result should be None or empty."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "uh huh",
            "result": [
                {"word": "uh",  "conf": 0.10, "start": 0.0, "end": 0.3},
                {"word": "huh", "conf": 0.15, "start": 0.3, "end": 0.5},
            ]
        })

        result = rec._process_vosk(_fake_audio())
        # All committed_text was [], all words filtered = nothing new
        assert result is None or result == ""

    def test_custom_confidence_threshold(self):
        """Custom threshold should be respected."""
        rec = _make_recognizer()
        rec.settings.get = MagicMock(side_effect=lambda key, default=None: {
            "fast_mode": False,
            "stability_lag": 2,
            "confidence_threshold": 0.8,  # high threshold
        }.get(key, default))
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "hello world",
            "result": [
                {"word": "hello", "conf": 0.95, "start": 0.0, "end": 0.5},
                {"word": "world", "conf": 0.60, "start": 0.5, "end": 1.0},
            ]
        })

        result = rec._process_vosk(_fake_audio())
        assert "hello" in result
        assert "world" not in result


# ─── #6: Partial Result Caching ──────────────────────────────────────────────

class TestPartialResultCaching:
    """P9-06: Skip re-parsing unchanged partial results."""

    def test_skip_when_partial_unchanged(self):
        """Repeated partial with same word count should return None."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = False
        rec.recognizer.PartialResult.return_value = json.dumps({
            "partial": "hello world"
        })

        # First call — 2 words, _last_partial_count was 0
        rec._process_vosk(_fake_audio())
        assert rec._last_partial_count == 2

        # Second call — same 2 words, should skip
        result2 = rec._process_vosk(_fake_audio())
        assert result2 is None

    def test_process_when_partial_grows(self):
        """Growing partial should be processed."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = False

        # First: 2 words
        rec.recognizer.PartialResult.return_value = json.dumps({"partial": "hello world"})
        rec._process_vosk(_fake_audio())
        assert rec._last_partial_count == 2

        # Second: 3 words — should process
        rec.recognizer.PartialResult.return_value = json.dumps({"partial": "hello world today"})
        rec._process_vosk(_fake_audio())
        assert rec._last_partial_count == 3

    def test_reset_clears_partial_count(self):
        """reset_state should clear _last_partial_count."""
        rec = _make_recognizer()
        rec._last_partial_count = 5
        rec.reset_state()
        assert rec._last_partial_count == 0

    def test_empty_partial_is_zero_count(self):
        """Empty partial result should have count 0."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = False
        rec.recognizer.PartialResult.return_value = json.dumps({"partial": ""})

        result = rec._process_vosk(_fake_audio())
        assert rec._last_partial_count == 0
        assert result is None


# ─── Regression ──────────────────────────────────────────────────────────────

class TestRecognizerRegression:
    """Ensure existing Vosk behavior isn't broken."""

    def test_full_result_resets_committed(self):
        """After a full result, committed_text should be empty."""
        rec = _make_recognizer()
        rec.committed_text = ["old", "words"]
        rec.recognizer.AcceptWaveform.return_value = True
        rec.recognizer.Result.return_value = json.dumps({
            "text": "new sentence",
            "result": [
                {"word": "new",      "conf": 0.99, "start": 0.0, "end": 0.3},
                {"word": "sentence", "conf": 0.95, "start": 0.3, "end": 0.8},
            ]
        })

        rec._process_vosk(_fake_audio())
        assert rec.committed_text == []

    def test_lag_strategy_holds_back_words(self):
        """With LAG=2, last 2 words of partial should be held back."""
        rec = _make_recognizer()
        rec.recognizer.AcceptWaveform.return_value = False
        rec.recognizer.PartialResult.return_value = json.dumps({
            "partial": "one two three four five"
        })

        result = rec._process_vosk(_fake_audio())
        # 5 words, LAG=2 → stable_len=3, committed=[one, two, three]
        assert rec._last_partial_count == 5
        if result:
            words = result.split()
            assert "one" in words
            assert "two" in words
            assert "three" in words
            assert "four" not in words
            assert "five" not in words
