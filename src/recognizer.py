import json
import os
import logging
from vosk import Model, KaldiRecognizer
from .config import MODEL_PATH, SAMPLE_RATE

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model not found at {MODEL_PATH}")
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Please download it.")
        
        logger.info(f"Loading model from {MODEL_PATH}")
        self.model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        logger.info("Model loaded successfully")

    def process_audio(self, data):
        """
        Process audio data chunks.
        Returns text if result found, else None.
        """
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            return result.get('text', '')
        return None

    def get_final_result(self):
        result = json.loads(self.recognizer.FinalResult())
        return result.get('text', '')
