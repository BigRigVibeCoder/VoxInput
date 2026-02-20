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
            if not os.path.exists(model_path):
                 if model_path != MODEL_PATH and os.path.exists(MODEL_PATH):
                     model_path = MODEL_PATH
                 else:
                     raise FileNotFoundError(f"Model not found at {model_path}")
            
            logger.info(f"Loading Vosk model from {model_path}")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        # --- Whisper Setup ---
        elif self.engine_type == "Whisper":
            size = self.settings.get("whisper_model_size", "base")
            logger.info(f"Loading Whisper model: {size}")

            # P2-01: Try faster-whisper first (4x faster, INT8, no CUDA required)
            faster_loaded = False
            try:
                from faster_whisper import WhisperModel
                compute = "int8"   # INT8 on CPU: fastest, minimal quality loss
                device = "cpu"
                try:
                    import torch
                    if torch.cuda.is_available():
                        device, compute = "cuda", "float16"
                except ImportError:
                    pass
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

            self.whisper_buffer = b""
            self.whisper_last_transcript = ""
            self.whisper_last_process_time = 0
            self.whisper_process_interval = 0.5
    
    def reset_state(self):
        """Reset streaming state (called on silence or manual stop)"""
        self.committed_text = []
        if self.engine_type == "Whisper":
            self.whisper_buffer = b""
            self.whisper_last_transcript = ""

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
        LAG = 0 if fast_mode else self.settings.get("stability_lag", 1)
        new_words_to_inject = []

        if not data:
            return None
            
        try:
            # 1. Check for Full Result (Sentence End)
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get('text', '')
                words = text.split()

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
                
                # Vosk Lag Strategy
                stable_len = max(0, len(words) - LAG)
                current_committed_len = len(self.committed_text)
                
                if stable_len > current_committed_len:
                    new_batch = words[current_committed_len : stable_len]
                    new_words_to_inject = new_batch
                    self.committed_text.extend(new_batch)
                    
        except Exception as e:
            logger.error(f"Vosk processing error: {e}")
            # In case of error, just reset stream state to avoid loop
            self.committed_text = [] 
            return None

        if new_words_to_inject:
            return " ".join(new_words_to_inject)
        return None

    def _process_whisper(self, data):
        # Whisper Strategy: Rolling Window + Common Prefix
        self.whisper_buffer += data
        now = time.time()
        
        # Throttle inference
        if now - self.whisper_last_process_time < self.whisper_process_interval:
            return None
        self.whisper_last_process_time = now
        
        # P1: Minimum buffer 0.5s (was 1.0s). Viable now with faster inference path.
        if len(self.whisper_buffer) < SAMPLE_RATE * 2 * 0.5:
            return None

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
                    self.whisper_buffer = b""
                    self.committed_text = [] # Start fresh
                    # Note: We lose the "context" for the NEXT sentence with this hard flush.
                    # But it prevents the drift/hallucination/lag issues.
                
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
            
        if len(self.whisper_buffer) == 0:
            return None
            
        logger.info("Finalizing Whisper buffer (Silence detected)...")
        try:
            # Similar to _process_whisper but with LAG = 0
            audio_np = np.frombuffer(self.whisper_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            
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
            self.whisper_buffer = b""
            self.committed_text = []
            
            if new_words:
                logger.info(f"Finalized flush: {new_words}")
                return " ".join(new_words)

        except Exception as e:
            logger.error(f"Error during finalize: {e}")
            
        return None


