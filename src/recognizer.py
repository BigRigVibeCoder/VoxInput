import json
import os
import logging
import audioop
import numpy as np

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

        if self.engine_type == "Whisper":
            if whisper is None:
                logger.error("Whisper module not found. Please install openai-whisper.")
                raise ImportError("openai-whisper not installed")
            
            size = self.settings.get("whisper_model_size", "base")
            logger.info(f"Loading Whisper model: {size}")
            try:
                self.model = whisper.load_model(size)
            except Exception as e:
                logger.warning(f"Failed to load Whisper with default device (likely CUDA error): {e}. Falling back to CPU.", exc_info=True)
                self.model = whisper.load_model(size, device="cpu")
            self.whisper_buffer = b""
            # Buffer threshold in bytes (SAMPLE_RATE * 2 bytes/sample * seconds)
            self.transcribe_threshold = SAMPLE_RATE * 2 * 3 # 3 seconds
        else:
            # Default to Vosk
            if Model is None:
                logger.error("Vosk module not found.")
                raise ImportError("vosk not installed")

            model_path = self.settings.get("model_path", MODEL_PATH)

            if not os.path.exists(model_path):
                logger.error(f"Model not found at {model_path}")
                # Fallback to default if custom fails
                if model_path != MODEL_PATH and os.path.exists(MODEL_PATH):
                     logger.info(f"Custom model path failed, falling back to default: {MODEL_PATH}")
                     model_path = MODEL_PATH
                else:
                     raise FileNotFoundError(f"Model not found at {model_path}. Please download it.")
            
            logger.info(f"Loading Vosk model from {model_path}")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        logger.info("Model loaded successfully")

    def process_audio(self, data):
        """
        Process audio data chunks.
        Returns text if result found, else None.
        """
        if self.engine_type == "Whisper":
            self.whisper_buffer += data
            # Simple approach: Transcribe if buffer is long enough
            # note: this is blocking and might cause audio drops if model is slow
            # ideally, this should be threaded, but let's keep it simple for now
            if len(self.whisper_buffer) >= self.transcribe_threshold:
                return self._transcribe_whisper()
            return None
        else:
            # Vosk Processing
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                return result.get('text', '')
            return None

    def _transcribe_whisper(self):
        try:
            # Convert raw bytes (int16) to numpy float32
            audio_np = np.frombuffer(self.whisper_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            
            result = self.model.transcribe(audio_np, fp16=False) # fp16=False for CPU safety
            text = result.get('text', '').strip()
            
            # Reset buffer
            self.whisper_buffer = b""
            
            if text:
                return text
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            self.whisper_buffer = b"" # Clear to prevent getting stuck
            
        return None

    def get_final_result(self):
        if self.engine_type == "Whisper":
            if len(self.whisper_buffer) > 0:
                return self._transcribe_whisper()
            return ""
        else:
            result = json.loads(self.recognizer.FinalResult())
            return result.get('text', '')
