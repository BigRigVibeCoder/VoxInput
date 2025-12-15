import unittest
import os
from src.recognizer import SpeechRecognizer
from src.config import MODEL_PATH
import pyaudio

class TestComponents(unittest.TestCase):
    def test_audio_device_availability(self):
        """Test that PyAudio can initialize and find devices."""
        p = pyaudio.PyAudio()
        try:
            count = p.get_device_count()
            # It's possible to have 0 devices in a cloud env, but we should at least not crash
            print(f"    Found {count} audio devices.") 
        finally:
            p.terminate()

    def test_recognizer_initialization(self):
        """Test that the SpeechRecognizer initializes and loads the model."""
        if not os.path.exists(MODEL_PATH):
            self.skipTest("Vosk model not found, skipping recognizer test.")
        
        try:
            rec = SpeechRecognizer()
            self.assertIsNotNone(rec.model, "Vosk model failed to load")
        except Exception as e:
            self.fail(f"SpeechRecognizer initialization failed: {e}")

if __name__ == '__main__':
    unittest.main()
