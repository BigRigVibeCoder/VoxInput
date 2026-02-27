import collections
import gc
import json
import logging
import os
import time

import numpy as np

# Try to import engines
try:
    from vosk import KaldiRecognizer, Model
except ImportError:
    Model = None
    KaldiRecognizer = None

try:
    import whisper
except ImportError:
    whisper = None

from .config import MODEL_PATH, SAMPLE_RATE
from .hardware_profile import HardwareProfile

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self):
        from .settings import SettingsManager
        self.settings = SettingsManager()
        self.engine_type = self.settings.get("speech_engine", "Vosk")

        # CLEANUP: Ensure previous models are cleared from GPU memory
        # We check for torch availability and CUDA
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
        except ImportError:
            pass

        logger.info(f"Initializing SpeechRecognizer with engine: {self.engine_type}")

        # --- State for Streaming ---
        self.committed_text = [] # List of words already injected for current utterance
        self.last_partial_time = 0

        # --- Vosk Setup ---
        if self.engine_type != "Whisper":
            if Model is None:
                logger.error("Vosk module not found.")
                raise ImportError("vosk not installed")

            model_path = self.settings.get("model_path", MODEL_PATH)

            # Resolve relative paths against the application root
            if not os.path.isabs(model_path):
                from .config import ROOT_DIR
                model_path = os.path.join(ROOT_DIR, model_path)

            # Validate it's an actual Vosk directory (must contain 'am' or 'conf')
            is_valid_vosk = os.path.isdir(model_path) and (
                os.path.exists(os.path.join(model_path, "am")) or
                os.path.exists(os.path.join(model_path, "conf"))
            )

            if not is_valid_vosk:
                logger.warning(f"Invalid Vosk model path '{model_path}'. Falling back to default.")
                model_path = MODEL_PATH
                if not os.path.exists(model_path):
                    raise FileNotFoundError(f"Default model not found at {model_path}")

            logger.info(f"Loading Vosk model from {model_path}")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        # --- Whisper Setup ---
        elif self.engine_type == "Whisper":
            size = self.settings.get("whisper_model_size", "base")
            logger.info(f"Loading Whisper model: {size}")

            # P2-01: Try faster-whisper. Use HardwareProfile for optimal device/compute.
            hw = HardwareProfile.detect()
            faster_loaded = False
            try:
                from faster_whisper import WhisperModel
                device  = hw.whisper_device
                compute = hw.whisper_compute
                self.model = WhisperModel(size, device=device, compute_type=compute)
                self.whisper_backend = "faster"
                faster_loaded = True
                logger.info(f"faster-whisper loaded: {size} on {device}/{compute}")
            except ImportError:
                logger.info("faster-whisper not installed — falling back to openai-whisper")
            except Exception as e:
                logger.warning(f"faster-whisper failed ({e}) — falling back to openai-whisper")

            if not faster_loaded:
                # Fallback: legacy openai-whisper
                if whisper is None:
                    raise ImportError("Neither faster-whisper nor openai-whisper are installed")
                try:
                    self.model = whisper.load_model(size)
                except Exception:
                    self.model = whisper.load_model(size, device="cpu")
                self.whisper_backend = "openai"
                logger.info(f"openai-whisper loaded: {size} on {self.model.device}")

            # P8-03: use a deque of raw chunk bytes instead of bytes concat.
            # np.concatenate() once at transcription time is O(N), not O(N^2).
            # Max 300 chunks = 30s @ 100ms chunks (prevents runaway growth).
            self.whisper_chunks: collections.deque[bytes] = collections.deque(maxlen=300)
            self.whisper_last_transcript = ""
            self.whisper_last_process_time = 0
            self.whisper_process_interval = 0.5

    def reset_state(self):
        """Reset streaming state (called on silence or manual stop)"""
        self.committed_text = []
        self._last_partial_count = 0   # P9-06: cached partial word count
        if self.engine_type == "Whisper":
            self.whisper_chunks.clear()
            self.whisper_last_transcript = ""

    def reset_recognizer(self):
        """Recreate the KaldiRecognizer after FinalResult() (PTT sessions).

        FinalResult() calls InputFinished() internally, putting the C-level
        recognizer in a terminal state. Subsequent AcceptWaveform() calls
        will crash with ASSERTION_FAILED. This method creates a fresh
        KaldiRecognizer from the existing model.
        """
        if self.engine_type != "Whisper" and self.model and KaldiRecognizer:
            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
            self.recognizer.SetWords(True)
            logger.info("Vosk recognizer reset (fresh KaldiRecognizer)")
        self.reset_state()

    def process_audio(self, data):
        """
        Process audio chunk and return NEW words to inject.
        Retuns string (words separated by spaces) or None.
        """
        if self.engine_type == "Whisper":
            return self._process_whisper(data)
        else:
            return self._process_vosk(data)

    def _process_vosk(self, data):
        # Vosk strategy: Lag-N Stabilization (P1-02/03)
        # fast_mode=True → LAG=0 (every word injected immediately, highest speed)
        # fast_mode=False → LAG=N (hold back N words until stable, higher accuracy)
        fast_mode = self.settings.get("fast_mode", False)
        LAG = 0 if fast_mode else self.settings.get("stability_lag", 2)
        new_words_to_inject = []

        if not data:
            return None

        try:
            # 1. Check for Full Result (Sentence End)
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get('text', '')
                words = text.split()

                # P9-02: Confidence filtering — drop low-confidence words
                # Vosk's "result" array contains per-word confidence scores
                conf_threshold = self.settings.get("confidence_threshold", 0.3)
                word_results = result.get('result', [])
                if word_results:
                    words = [
                        wr['word'] for wr in word_results
                        if wr.get('conf', 1.0) >= conf_threshold
                    ]

                # P1-02: Full result = sentence confirmed final by Vosk.
                # Inject ALL uncommitted words with zero lag — no reason to hold back.
                new_words_to_inject = words[len(self.committed_text):]

                # Reset for next sentence
                self.committed_text = []

            # 2. Check Partial Result (Streaming)
            else:
                partial = json.loads(self.recognizer.PartialResult())
                text = partial.get('partial', '')
                words = text.split()

                # P9-06: skip processing if partial hasn't grown
                if len(words) == self._last_partial_count:
                    return None
                self._last_partial_count = len(words)

                # Vosk Lag Strategy
                stable_len = max(0, len(words) - LAG)
                current_committed_len = len(self.committed_text)

                if stable_len > current_committed_len:
                    new_batch = words[current_committed_len : stable_len]
                    new_words_to_inject = new_batch
                    self.committed_text.extend(new_batch)

        except Exception as e:
            logger.error(f"Vosk processing error: {e}")
            # Auto-recover: reset recognizer to prevent C-level abort on next call
            try:
                self.reset_recognizer()
                logger.info("Auto-recovered from Vosk error (recognizer reset)")
            except Exception:
                pass
            return None

        if new_words_to_inject:
            return " ".join(new_words_to_inject)
        return None

    def _process_whisper(self, data):
        # P8-03: append chunk to deque — O(1), no copy
        self.whisper_chunks.append(data)
        now = time.time()

        # Throttle inference
        if now - self.whisper_last_process_time < self.whisper_process_interval:
            return None
        self.whisper_last_process_time = now

        # P1: Minimum buffer 0.5s
        total_bytes = sum(len(c) for c in self.whisper_chunks)
        if total_bytes < SAMPLE_RATE * 2 * 0.5:
            return None

        # P10: Use C Extension (librms.so) for native PCM -> Normalized Float32 casting.
        # Eliminates O(N) python numpy loops, GIL locking, and intermediate arrays.
        from .c_ext import pcm_to_float32
        audio_np = pcm_to_float32(self.whisper_chunks)

        try:
            # P2-02/03: Route to faster-whisper or openai-whisper backend
            if getattr(self, "whisper_backend", "openai") == "faster":
                # faster-whisper returns a generator of segments
                silence_ms = int(self.settings.get("silence_duration", 0.6) * 1000)
                segments, _ = self.model.transcribe(
                    audio_np,
                    beam_size=1,
                    language="en",
                    vad_filter=True,           # P2-05: built-in Silero VAD
                    vad_parameters=dict(
                        threshold=0.5,
                        min_silence_duration_ms=silence_ms
                    )
                )
                current_transcript = " ".join(s.text.strip() for s in segments)
            else:
                # Legacy openai-whisper path
                result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language="en")
                current_transcript = result.get("text", "").strip()
            words = current_transcript.split()
            # P1-03: fast_mode=True → LAG=0 (inject every word immediately)
            # Higher lag for Whisper by default as it fluctuates more at the tail
            fast_mode = self.settings.get("fast_mode", False)
            LAG = 0 if fast_mode else self.settings.get("stability_lag", 2)

            stable_len = max(0, len(words) - LAG)
            current_committed_len = len(self.committed_text)

            new_words_to_inject = []

            if stable_len > current_committed_len:
                # Check for consistency
                # Does words[0:committed] match committed_text?
                # If not, we have a divergence.
                # (e.g. committed "Recall", now "We call").
                # Since we can't backspace efficiently (injector supports it but logic is complex),
                # We simply effectively "fork" the reality and just append words.
                # It's an imperfect trade-off for speed.

                new_batch = words[current_committed_len : stable_len]
                new_words_to_inject = new_batch
                self.committed_text.extend(new_batch)

            if new_words_to_inject:
                text_result = " ".join(new_words_to_inject)

                # Heuristic: If we successfully committed a full sentence, flush the buffer
                # to prevent infinite buffer growth and improve future responsiveness.
                if new_words_to_inject[-1].endswith(('.', '!', '?')):
                    logger.info("Sentence completed. Flushing Whisper buffer.")
                    self.whisper_chunks.clear()
                    self.committed_text = []

                return text_result

        except Exception as e:
            logger.error(f"Whisper inference error: {e}")

        return None

    def finalize(self):
        """
        Called when silence is detected. Forces processing of any remaining buffer
        with zero lag. Handles both Vosk and Whisper engines. (P1)
        """
        # P1: Vosk finalize — flush any uncommitted partial words
        if self.engine_type != "Whisper":
            try:
                result = json.loads(self.recognizer.FinalResult())
                text = result.get('text', '')
                words = text.split()
                uncommitted = words[len(self.committed_text):]
                self.committed_text = []
                if uncommitted:
                    logger.info(f"Vosk final flush: {uncommitted}")
                    return " ".join(uncommitted)
            except Exception as e:
                logger.error(f"Vosk finalize error: {e}")
            return None

        # Whisper finalize — flush rolling buffer
        if not self.model:
            return None

        if len(self.whisper_chunks) == 0:
            return None

        logger.info("Finalizing Whisper buffer (Silence detected)...")
        try:
            # P8-03: concatenate once
            audio_np = np.concatenate(
                [np.frombuffer(c, dtype=np.int16) for c in self.whisper_chunks]
            ).astype(np.float32) / 32768.0

            # Safety check for empty tensor
            if audio_np.size == 0:
                return None

            result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language='en')
            current_transcript = result.get('text', '').strip()

            # Logic: We just want to output whatever is NEW compared to committed
            words = current_transcript.split()
            current_committed_len = len(self.committed_text)

            new_words = []
            if len(words) > current_committed_len:
                new_words = words[current_committed_len:]

            # Flush everything
            self.whisper_chunks.clear()
            self.committed_text = []

            if new_words:
                logger.info(f"Finalized flush: {new_words}")
                return " ".join(new_words)

        except Exception as e:
            logger.error(f"Error during finalize: {e}")

        return None


