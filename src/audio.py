import logging
import collections

import pyaudio

from .config import CHANNELS, CHUNK_SIZE, SAMPLE_RATE
from .logger import TRACE

logger = logging.getLogger(__name__)

class AudioCapture:
    def __init__(self) -> None:
        self.pa = pyaudio.PyAudio()
        self.stream = None
        # P8-05: deque(maxlen=50) is 3–4× faster than queue.Queue for SPSC.
        # PyAudio callback (producer) and _process_loop (consumer) never overlap.
        # maxlen=50 auto-drops oldest when full — same freshness guarantee.
        self._buf: collections.deque[bytes] = collections.deque(maxlen=50)
        self.is_running = False

    def start(self) -> None:
        if self.is_running:
            return

        try:
            self.is_running = True
            self._buf.clear()  # Clear old audio

            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._callback
            )
            self.stream.start_stream()
            logger.log(TRACE, "audio.stream.started rate=%d chunk=%d", SAMPLE_RATE, CHUNK_SIZE)
            logger.info("Audio stream started.")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self.is_running = False
            raise

    def _callback(self, in_data: bytes | None, frame_count: int, time_info: dict, status: int) -> tuple[None, int]:
        """Hardware callback pushing audio frames.
        
        FAILURE MODE: 
          - This runs on a dedicated C-thread spawned by PortAudio.
          - If this method blocks for any reason (e.g. heavy logging, sleep, or lock contention),
            the audio subsystem will drop frames or completely deadlock the ALSA/Pulse driver.
            
        SAFETY:
          - We use a lock-free deque (maxlen=50). deque.append is atomic and non-blocking in CPython.
        """
        if self.is_running:
            self._buf.append(in_data)  # deque drops oldest when full — no exception
        return (None, pyaudio.paContinue)

    def stop(self) -> None:
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            logger.log(TRACE, "audio.stream.stopped")

    def get_data(self) -> bytes | None:
        try:
            return self._buf.popleft()
        except IndexError:
            return None

    def terminate(self) -> None:
        self.stop()
        self.pa.terminate()
