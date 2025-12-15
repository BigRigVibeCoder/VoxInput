import json
import os
import logging
import audioop
import numpy as np
import io
import wave
from abc import ABC, abstractmethod
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel

from .config import MODEL_PATH, SAMPLE_RATE, WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

class SpeechEngine(ABC):
    @abstractmethod
    def process_audio(self, data: bytes) -> str:
        """Process chunk of audio, return string if recognition occurs, else None/Empty"""
        pass

    @abstractmethod
    def terminate(self):
        pass

class VoskEngine(SpeechEngine):
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
             raise FileNotFoundError(f"Vosk Model not found at {MODEL_PATH}")
        
        logger.info(f"Loading Vosk model from {MODEL_PATH}")
        self.model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        logger.info("Vosk Model loaded")

    def process_audio(self, data: bytes) -> str:
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '')
            if text:
                logger.info(f"[Vosk] Recognized: {text}")
            return text
        return None

    def terminate(self):
        pass

class WhisperEngine(SpeechEngine):
    def __init__(self):
        logger.info(f"Loading Faster-Whisper model ({WHISPER_MODEL_SIZE})...")
        # Run on CPU with INT8 quantization for speed on standard machines
        self.model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        logger.info("Whisper Model loaded")
        
        self.buffer = io.BytesIO()
        self.silence_frames = 0
        self.has_speech = False
        
        # VAD Constants
        self.SILENCE_THRESHOLD = 500 # Adjust based on noise, maybe dynamic?
        self.SILENCE_DURATION = int(SAMPLE_RATE / 4096 * 0.8) # ~0.8 seconds of silence to trigger
        # (Chunk size is usually 4096 in audio.py? Need to be careful. audio.py might be 1024 or 4096)
        # config.py CHUNK_SIZE = 4096 (checked before)
        # 16000 Hz / 4096 ~= 4 chunks per second. 
        # So wait for ~3-4 silent chunks.

    def process_audio(self, data: bytes) -> str:
        # 1. Calculate energy
        rms = audioop.rms(data, 2) # width=2 for int16
        
        # 2. VAD Logic
        if rms > self.SILENCE_THRESHOLD:
            self.has_speech = True
            self.silence_frames = 0
        else:
            if self.has_speech:
                self.silence_frames += 1
        
        self.buffer.write(data)
        
        # 3. Trigger Transcription
        # If we had speech, and now we have enough silence, TRANSCRIPTION TIME!
        if self.has_speech and self.silence_frames > 4: # ~1 second silence
            logger.info("[Whisper] Silence detected, transcribing buffer...")
            text = self._transcribe()
            
            # Reset
            self.buffer = io.BytesIO()
            self.silence_frames = 0
            self.has_speech = False
            return text
            
        return None

    def _transcribe(self) -> str:
        # Convert buffer to numpy array float32
        self.buffer.seek(0)
        # Use numpy to read buffer. 
        # faster-whisper wants np.ndarray[np.float32]
        # Data is Int16.
        val = np.frombuffer(self.buffer.read(), dtype=np.int16)
        val = val.flatten().astype(np.float32) / 32768.0
        
        segments, info = self.model.transcribe(val, beam_size=5, language="en")
        
        full_text = []
        for segment in segments:
            full_text.append(segment.text.strip())
            
        result = " ".join(full_text)
        if result:
            logger.info(f"[Whisper] Result: {result}")
        return result

    def terminate(self):
        pass

class SpeechRecognizer:
    def __init__(self, engine_type="vosk"):
        self.engine = None
        self.set_engine(engine_type)

    def set_engine(self, engine_type):
        logger.info(f"Switching engine to: {engine_type}")
        if self.engine:
            self.engine.terminate()
            
        try:
            if engine_type == "whisper":
                self.engine = WhisperEngine()
            else:
                self.engine = VoskEngine()
        except Exception as e:
            logger.error(f"Failed to initialize {engine_type}: {e}")
            logger.warning("Falling back to Vosk")
            self.engine = VoskEngine()

        self.engine_type = engine_type

    def process_audio(self, data):
        return self.engine.process_audio(data)
