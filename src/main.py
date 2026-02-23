import queue as _queue
import signal
import sys
import threading
import time

from gi.repository import GLib
from pynput import keyboard

from .audio import AudioCapture
from .config import HOTKEY, PTT_KEY
from .injection import TextInjector, VoicePunctuationBuffer
from .homophones import fix_homophones                     # P9-D: homophone correction
from .audio_feedback import AudioFeedback                  # PTT beeps
from .logger import init_logging, get_logger         # P7: enterprise logging
from .mic_enhancer import MicEnhancer
from .recognizer import SpeechRecognizer
from .settings import SettingsManager
from .spell_corrector import SpellCorrector
from .ui import Gtk, SystemTrayApp
from .c_ext import rms_int16, using_c_extension      # P8: C RMS extension
from .word_db import WordDatabase

# P7: Enterprise logging — TRACE level, SQLite black box, sys.excepthook
# Level resolved from .env file (LOG_LEVEL=TRACE by default on desktop install).
init_logging("voxinput")
logger = get_logger(__name__)


class VoxInputApp:
    def __init__(self):
        self._model_ready = False          # gate: block toggle until loaded

        # ── Fast path: everything the user sees immediately ────
        self.audio    = AudioCapture()
        self.settings = SettingsManager()
        self.mic      = MicEnhancer(self.settings)
        self.mic.restore_settings()

        self.is_listening = False
        self.should_quit  = False
        self.processing_thread = None
        self._ptt_active = False  # True while PTT key is physically held
        self._audio_fb = AudioFeedback()  # PTT beep sounds

        # Stubs — replaced by background thread when ready
        self.recognizer = None
        self.injector   = None
        self.spell      = None
        self.word_db    = None
        self._punct_buf = VoicePunctuationBuffer()  # P4-02: cross-batch voice cmds

        # Injection queue + thread (safe to start early; drains empty queue)
        self._injection_queue: _queue.Queue = _queue.Queue(maxsize=100)
        self._injection_thread = threading.Thread(
            target=self._injection_loop, daemon=True, name="injection"
        )
        self._injection_thread.start()

        # ── UI appears here ─────────────────────────────────────
        self.ui = SystemTrayApp(
            toggle_callback=self.toggle_listening,
            quit_callback=self.quit_app,
            engine_change_callback=self.reload_engine
        )
        # Direct stop callback for settings dialog (bypasses toggle guard)
        self.ui._app_stop_listening = self.stop_listening
        # Show loading state in tray
        self.ui.indicator.set_title("VoxInput — Loading model…")

        # ── Background: load heavy components then auto-listen ──
        threading.Thread(target=self._load_models, daemon=True, name="model-load").start()

    def _load_models(self):
        """Background thread: loads Vosk/Whisper model, SymSpell dict, injection backend.
        Fires start_listening() on the GTK main thread when done."""
        try:
            logger.info("Background model load starting...")
            # Word database (protected words list) — seed on first run
            import os
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "data", "custom_words.db"
            )
            self.word_db = WordDatabase(db_path)
            # Seed with initial dataset if DB is empty (first run)
            try:
                from data.seed_words import SEED_WORDS
                self.word_db.seed(SEED_WORDS)
            except Exception as seed_err:
                logger.warning(f"Word DB seed skipped: {seed_err}")

            self.recognizer = SpeechRecognizer()
            self.spell      = SpellCorrector(self.settings, word_db=self.word_db)
            self.injector   = TextInjector()
            self._model_ready = True
            logger.info("Background model load complete — auto-starting listening.")
            GLib.idle_add(self._on_models_ready)
        except Exception as e:
            logger.critical(f"Model load failed: {e}", exc_info=True)
            GLib.idle_add(self.ui.indicator.set_title, f"VoxInput — Load failed: {e}")

    def _on_models_ready(self):
        """Called on GTK main thread once models are loaded."""
        self.ui.indicator.set_title("VoxInput (Idle)")
        # Don't auto-start in PTT mode — wait for key press
        if not self.settings.get("push_to_talk", False):
            self.start_listening()
        else:
            logger.info("PTT mode active — waiting for key press.")
        return False             # one-shot GLib idle


    def reload_engine(self):
        if not self._model_ready:
            return  # initial load not done yet
        logger.info("Reloading speech engine...")
        was_listening = self.is_listening
        if was_listening:
            self.stop_listening()
            
        try:
            # Re-initialize recognizer (reads new settings)
            self.recognizer = SpeechRecognizer()
            logger.info("Engine reloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to reload engine: {e}")
            return

        if was_listening:
            self.start_listening()

    def toggle_listening(self):
        if not self._model_ready:
            self.ui.indicator.set_title("VoxInput — Still loading model, please wait…")
            GLib.timeout_add(2000, lambda: self.ui.indicator.set_title("VoxInput — Loading model…"))
            return
        # Block toggle hotkey when PTT mode is on
        if self.settings.get("push_to_talk", False):
            logger.info("Toggle blocked — PTT mode active. Use PTT key instead.")
            return
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        if self.is_listening:
            logger.warning("Already listening.")
            return
            
        logger.info("Starting listening... (C_RMS=%s)", using_c_extension())
        self.is_listening = True
        self.ui.set_listening_state(True)
        self.recognizer.reset_state()
        self.audio.start()

        # P8-02: cache hot-path settings so _process_loop never calls settings.get() per-chunk
        self._sil_threshold: int = int(self.settings.get("silence_threshold", 500))
        self._sil_duration:  float = float(self.settings.get("silence_duration", 0.6))
        # P9-B: Adaptive silence — EMA noise floor tracking
        self._adaptive_silence = self.settings.get("adaptive_silence", True)
        self._noise_floor_ema: float = float(self._sil_threshold)  # seed with manual threshold
        self._ema_alpha: float = 0.05  # smoothing factor (lower = slower adaptation)

        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            return

        logger.info("Stopping listening...")
        self.is_listening = False
        self.ui.set_listening_state(False)
        self.ui.update_osd("", 0.0)   # P5: clear OSD on stop
        self.audio.stop()

        if self.processing_thread:
            # P0-04: 8s timeout — must outlast worst-case CPU Whisper inference
            self.processing_thread.join(timeout=8.0)
            if self.processing_thread.is_alive():
                logger.warning("Processing thread did not exit cleanly within 8s")
            self.processing_thread = None

    def _injection_loop(self):
        """Dedicated thread: drains injection queue → xdotool. (P1-04)"""
        while not self.should_quit:
            try:
                text = self._injection_queue.get(timeout=0.1)
                self.injector.type_text(text)
            except _queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Injection error: {e}")

    def _process_loop(self):
        silence_start_time = None
        osd_words: list[str] = []   # P5: accumulate words for OSD display
        _last_osd_words = ""        # P8-04: only marshal to GTK when content changes
        _last_osd_level  = -1.0
        _OSD_LEVEL_BAND  = 0.05     # only update OSD if level shifts by >5%

        while self.is_listening and not self.should_quit:
            data = self.audio.get_data()
            if data:
                # P9-04: drain backlog — if >3 chunks queued, concatenate to
                # prevent drops under CPU load (still one RMS + one Vosk call)
                backlog = len(self.audio._buf)
                if backlog > 3:
                    extra = []
                    while self.audio._buf:
                        extra.append(self.audio._buf.popleft())
                    data = data + b"".join(extra)
                    logger.debug(f"Drained {backlog} backlogged chunks")
                # P8-01: C extension RMS (single-pass, no float64 array alloc).
                # Falls back to numpy if librms.so not present.
                rms = int(rms_int16(data))

                # P8-04: OSD rate-limit — only marshal to GTK when content changes
                level = min(rms / 8000.0, 1.0)
                osd_str = " ".join(osd_words[-8:])
                level_changed = abs(level - _last_osd_level) > _OSD_LEVEL_BAND
                words_changed  = osd_str != _last_osd_words
                if level_changed or words_changed:
                    self.ui.update_osd(osd_str, level)
                    _last_osd_words  = osd_str
                    _last_osd_level  = level

                # P9-B: Adaptive silence — update noise floor EMA
                if self._adaptive_silence:
                    if rms < self._sil_threshold:
                        # Update EMA when in "silence" range
                        self._noise_floor_ema = (
                            self._ema_alpha * rms +
                            (1 - self._ema_alpha) * self._noise_floor_ema
                        )
                        # Set threshold at 2.5× noise floor (with a minimum)
                        self._sil_threshold = max(200, int(self._noise_floor_ema * 2.5))

                # P8-02: use cached threshold/duration (no settings.get per chunk)
                if rms < self._sil_threshold:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif time.time() - silence_start_time > self._sil_duration:
                        try:
                            final_text = self.recognizer.finalize()
                            if final_text:
                                logger.info(f"Finalized (Silence): {final_text}")
                                self._enqueue_injection(final_text)
                            # Flush any pending cross-batch number
                            if self.spell:
                                num_flush = self.spell.flush_pending_number()
                                if num_flush:
                                    punctuated = self._punct_buf.process(num_flush)
                                    if punctuated:
                                        self._injection_queue.put_nowait(punctuated)
                            # Flush any pending multi-word command prefix
                            flushed = self._punct_buf.flush()
                            if flushed:
                                self._injection_queue.put_nowait(flushed)
                                osd_words.clear()
                        except Exception as e:
                            logger.error(f"Error finalizing: {e}")
                        silence_start_time = None
                else:
                    silence_start_time = None

                # --- Normal Processing ---
                try:
                    text = self.recognizer.process_audio(data)
                    if text:
                        logger.info(f"Recognized: {text}")
                        # PTT mode: display on OSD but don't inject yet
                        # (full-context injection happens on key release)
                        if self._ptt_active:
                            osd_words.extend(text.split())
                        else:
                            self._enqueue_injection(text)
                            osd_words.extend(text.split())
                except Exception as e:
                    logger.error(f"Error processing audio: {e}", exc_info=True)
            else:
                time.sleep(0.01)

    def _enqueue_injection(self, text: str):
        """Spell-correct then push to injection queue (non-blocking). (P3)"""
        if not self.spell or not self.injector:
            return  # models not ready yet
        try:
            corrected = self.spell.correct(text)  # P3: SymSpellPy + ASR rules
            corrected = fix_homophones(corrected)  # P9-D: homophone correction
            punctuated = self._punct_buf.process(corrected)  # P4-02: voice punctuation
            if punctuated:
                self._injection_queue.put_nowait(punctuated)
        except _queue.Full:
            logger.warning("Injection queue full — dropping word batch (engine too slow?)")

    def quit_app(self):
        self.should_quit = True
        self.stop_listening()
        self.audio.terminate()
        Gtk.main_quit()
        sys.exit(0)

    # ── Push-to-Talk ──────────────────────────────────────────────

    def _get_ptt_key(self) -> str:
        """Get the configured PTT key string (falls back to config default)."""
        return self.settings.get("ptt_key", PTT_KEY)

    def _on_ptt_press(self, key):
        """pynput callback: key pressed."""
        if self._ptt_active:
            return  # already held — ignore repeat events
        if not self.settings.get("push_to_talk", False):
            return  # PTT mode not enabled
        try:
            if str(key) == self._get_ptt_key() and self._model_ready:
                self._ptt_active = True
                if self.settings.get("ptt_audio_feedback", True):
                    self._audio_fb.play_press()
                GLib.idle_add(self.start_listening)
        except Exception:
            pass

    def _on_ptt_release(self, key):
        """pynput callback: key released → full-context finalize + inject."""
        if not self._ptt_active:
            return
        try:
            if str(key) == self._get_ptt_key():
                self._ptt_active = False
                GLib.idle_add(self._ptt_finalize)
        except Exception:
            pass

    def _ptt_finalize(self):
        """Full-context PTT pipeline: finalize → correct → inject entire sentence."""
        if not self.recognizer or not self.spell:
            self.stop_listening()
            return

        try:
            # 1. Get the complete transcript
            final_text = self.recognizer.finalize()

            # 2. Also flush any pending number from spell corrector
            num_flush = ""
            if self.spell:
                num_flush = self.spell.flush_pending_number() or ""

            # 3. Combine and run full-context correction pipeline
            full_text = ((final_text or "") + " " + num_flush).strip()

            if full_text:
                logger.info(f"PTT full-context raw: {full_text}")
                # Full-sentence spell correction (much better with context)
                corrected = self.spell.correct(full_text)
                # Full-sentence homophone resolution
                corrected = fix_homophones(corrected)
                # Voice punctuation
                from .injection import apply_voice_punctuation
                corrected = apply_voice_punctuation(corrected)

                logger.info(f"PTT full-context corrected: {corrected}")
                if corrected.strip():
                    self._injection_queue.put_nowait(corrected.strip())

        except Exception as e:
            logger.error(f"PTT finalize error: {e}", exc_info=True)
        finally:
            # Reset Vosk recognizer for next PTT session (FinalResult kills it)
            if self.recognizer:
                self.recognizer.reset_recognizer()
            # Always stop listening and play release beep
            self.stop_listening()
            if self.settings.get("ptt_audio_feedback", True):
                self._audio_fb.play_release()

    def run(self):
        # Setup signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.quit_app())
        signal.signal(signal.SIGUSR1, lambda s, f: self.toggle_listening())

        # Push-to-talk key listener (always running; only acts when setting is on)
        self._ptt_listener = keyboard.Listener(
            on_press=self._on_ptt_press,
            on_release=self._on_ptt_release,
        )
        self._ptt_listener.daemon = True
        self._ptt_listener.start()

        # Run UI loop
        Gtk.main()

    def _listen_hotkeys(self):
        
        def on_activate():
            # Run in main thread context if possible, or careful with Gtk
            # Gtk is not thread safe. Use GLib.idle_add
            GLib.idle_add(self.toggle_listening)

        # Parse hotkey string or hardcode for now
        # simple wrapper
        with keyboard.GlobalHotKeys({
            HOTKEY: on_activate
        }) as h:
            h.join()

if __name__ == "__main__":
    try:
        app = VoxInputApp()
        logger.info("VoxInput Application Started")
        app.run()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)
