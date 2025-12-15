import pyaudio
import queue
import logging
from .config import SAMPLE_RATE, CHANNELS, CHUNK_SIZE

logger = logging.getLogger(__name__)

class AudioCapture:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.queue = queue.Queue()
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        
        try:
            self.is_running = True
            self.queue.queue.clear() # Clear old audio
            
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._callback
            )
            self.stream.start_stream()
            logger.info("Audio stream started.")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self.is_running = False
            raise

    def _callback(self, in_data, frame_count, time_info, status):
        if self.is_running:
            self.queue.put(in_data)
        return (None, pyaudio.paContinue)

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def get_data(self):
        if not self.queue.empty():
            return self.queue.get()
        return None

    def terminate(self):
        self.stop()
        self.pa.terminate()
