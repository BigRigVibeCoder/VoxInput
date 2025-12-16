import json
import os
import logging
import audioop
import numpy as np
import time

# Try to import engines
try:
    from vosk import Model, KaldiRecognizer
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
            if whisper is None:
                logger.error("Whisper module not found.")
                raise ImportError("openai-whisper not installed")
            
            size = self.settings.get("whisper_model_size", "base")
            logger.info(f"Loading Whisper model: {size}")
            try:
                self.model = whisper.load_model(size)
            except Exception as e:
                logger.warning(f"Failed to load Whisper with default device: {e}. Using CPU.")
                self.model = whisper.load_model(size, device="cpu")
            
            self.whisper_buffer = b""
            # Whisper Streaming State
            self.whisper_last_transcript = ""
            self.whisper_last_process_time = 0
            self.whisper_process_interval = 0.5 # Run inference every 500ms
    
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
        # Vosk strategy: Lag-N Stabilization
        # We hold back the last N words until they are stable or the sentence ends.
        LAG = 1 
        new_words_to_inject = []

        # 1. Check for Full Result (Sentence End)
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '')
            words = text.split()
            
            # Inject whatever hasn't been committed yet
            if len(words) > len(self.committed_text):
                new_words_to_inject = words[len(self.committed_text):]
            
            # Reset for next sentence
            self.committed_text = []
        
        # 2. Check Partial Result (Streaming)
        else:
            partial = json.loads(self.recognizer.PartialResult())
            text = partial.get('partial', '')
            words = text.split()
            
            # Simple stability check:
            # If we have [A, B, C, D] and we committed [A, B]
            # And LAG=1, we can commit C if we have D.
            
            # We trust partials up to length-LAG
            stable_len = max(0, len(words) - LAG)
            
            current_committed_len = len(self.committed_text)
            
            if stable_len > current_committed_len:
                # We have new stable words!
                # E.g. Words=[A,B,C,D], Committed=[A,B], Stable=3 (A,B,C).
                # New to inject = Words[2:3] = [C]
                
                # Sanity check: ensure the prefix matches committed text
                # (Vosk sometimes changes its mind about the past, though rarely for stable prefixes)
                # If it changed the past structurally, we might just have to ignore the divergence 
                # or output the new suffix. Let's assume append-only for now.
                
                new_batch = words[current_committed_len : stable_len]
                new_words_to_inject = new_batch
                self.committed_text.extend(new_batch)

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
        
        # Don't process if buffer is too short (< 1s) to save CPU
        if len(self.whisper_buffer) < SAMPLE_RATE * 2 * 1.0:
            return None

        try:
            # Transcribe current buffer
            audio_np = np.frombuffer(self.whisper_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Using beam_size=1 and fp16=False for speed
            result = self.model.transcribe(audio_np, fp16=False, beam_size=1, language='en')
            current_transcript = result.get('text', '').strip()
            
            # Normalization
            # Whisper output can include punctuation. Vosk does not.
            # We want to enable "streaming" feel.
            
            # Compare with last transcript to find stable prefix
            # This is tricky because "The cat" vs "The car"
            # We accept words that appear in BOTH the previous and current hypothesis?
            # Or just output whatever exceeds committed length?
            
            # Better Strategy for Whisper:
            # Just output the words that are new compared to committed_text.
            # BUT: Whisper rewrites the whole sentence.
            # If committed: "The quick"
            # Current: "The quick brown" -> Inject "brown"
            # Next: "The quick brown fox" -> Inject "fox"
            # If Current: "The thick brown..." -> WE HAVE A PROBLEM. We already injected "quick".
            # We cannot delete injection.
            
            # So we use a "Stability buffer" too.
            # We only commit if the word is "far enough back" from the edge.
            
            words = current_transcript.split()
            LAG = 2 # Higher lag for Whisper as it fluctuates more at the tail
            
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
                return " ".join(new_words_to_inject)

        except Exception as e:
            logger.error(f"Whisper inference error: {e}")
            
        return None
