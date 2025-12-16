import pyaudio
import queue
import logging
import audioop
from .config import SAMPLE_RATE, CHANNELS, CHUNK_SIZE, INPUT_DEVICE_INDEX

logger = logging.getLogger(__name__)

class AudioCapture:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.queue = queue.Queue()
        self.is_running = False
        self.device_index = INPUT_DEVICE_INDEX

    def set_device_index(self, index):
        self.device_index = index

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
                stream_callback=self._callback,
                input_device_index=self.device_index
            )
            if self.device_index is not None:
                logger.info(f"Using Audio Device Index: {self.device_index}")
            else:
                logger.info("Using System Default Audio Device")
            self.stream.start_stream()
            logger.info("Audio stream started.")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self.is_running = False
            raise

    def _callback(self, in_data, frame_count, time_info, status):
        if self.is_running:
            # Apply gain if needed (hardware signal is very low)
            # Multiplying by 4 to boost volume safely
            try:
                # audioop.mul(fragment, width, factor)
                # width=2 for 16-bit audio
                gain_data = audioop.mul(in_data, 2, 4.0)
                self.queue.put(gain_data)
            except Exception as e:
                logger.error(f"Error applying gain: {e}")
                self.queue.put(in_data)
        return (None, pyaudio.paContinue)

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
            
            try:
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")
            finally:
                self.stream = None
        
        # Clear queue to prevent memory buildup
        self.queue.queue.clear()

    def get_data(self):
        if not self.queue.empty():
            return self.queue.get()
        return None

    def terminate(self):
        self.stop()
        self.pa.terminate()

class MicTester:
    def __init__(self, device_index=None):
        self.device_index = device_index
        self.pa = pyaudio.PyAudio()

    def run_test(self, duration=5, progress_callback=None):
        chunks = []
        try:
            # 1. Record
            if progress_callback: progress_callback("Recording...")
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=self.device_index
            )
            
            for _ in range(0, int(SAMPLE_RATE / CHUNK_SIZE * duration)):
                data = stream.read(CHUNK_SIZE)
                # Apply same gain for meaningful test
                gain_data = audioop.mul(data, 2, 4.0)
                chunks.append(gain_data)
                
            stream.stop_stream()
            stream.close()
            
            # 2. Playback
            if progress_callback: progress_callback("Playing back...")
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True
            )
            
            for data in chunks:
                stream.write(data)
                
            stream.stop_stream()
            stream.close()
            
            if progress_callback: progress_callback("Done")
            
        except Exception as e:
            logger.error(f"Mic Test Failed: {e}")
            if progress_callback: progress_callback(f"Error: {str(e)[:20]}...")
        finally:
            self.pa.terminate()
