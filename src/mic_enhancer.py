"""
MicEnhancer — Ubuntu Linux microphone signal enhancement. (Phase 6)

Controls PulseAudio/PipeWire input gain, noise suppression (WebRTC AEC),
and ALSA hardware mic boost without requiring any external audio tools
beyond what Ubuntu ships by default.

All subprocess calls use pactl/amixer — no extra packages needed.
Settings are persisted via SettingsManager so they restore on next launch.
"""
import logging
import re
import subprocess
import time

logger = logging.getLogger(__name__)


class MicEnhancer:
    """
    Microphone signal enhancement via PulseAudio/PipeWire (Ubuntu).

    Controls:
      - Input volume (0-150%, software gain via pactl)
      - Noise suppression (WebRTC AEC via module-echo-cancel)
      - ALSA Mic Boost (hardware pre-amp via amixer)
      - Auto-calibrate (measures ambient noise floor, recommends threshold)
    """

    def __init__(self, settings):
        self.settings = settings
        self._noise_module_id: str | None = settings.get("_noise_module_id")

    # ─── Input Volume ────────────────────────────────────────────────────

    def get_input_volume(self) -> int:
        """Return current input volume as 0–150 (100 = unity gain)."""
        source = self._source()
        try:
            out = subprocess.check_output(
                ["pactl", "get-source-volume", source], text=True, timeout=3
            )
            m = re.search(r"(\d+)%", out)
            return int(m.group(1)) if m else 100
        except Exception as e:
            logger.warning(f"get_input_volume: {e}")
            return 100

    def set_input_volume(self, percent: int):
        """Set input volume 0–150%. Values >100 apply software boost."""
        percent = max(0, min(150, int(percent)))
        try:
            subprocess.run(
                ["pactl", "set-source-volume", self._source(), f"{percent}%"],
                check=True, timeout=3, capture_output=True
            )
            self.settings.set("mic_volume", percent)
            logger.info(f"Mic volume → {percent}%")
        except Exception as e:
            logger.error(f"set_input_volume({percent}): {e}")

    # ─── Noise Suppression ──────────────────────────────────────────────

    def enable_noise_suppression(self):
        """Load PulseAudio module-echo-cancel with WebRTC AEC."""
        if self._noise_module_id:
            logger.debug("Noise suppression already active")
            return
        source = self._source()
        try:
            result = subprocess.check_output([
                "pactl", "load-module", "module-echo-cancel",
                f"source_master={source}",
                "source_name=VoxInputDenoised",
                "aec_method=webrtc",
                "source_properties=device.description='VoxInput Denoised Mic'"
            ], text=True, timeout=8)
            self._noise_module_id = result.strip()
            self.settings.set("noise_suppression", True)
            self.settings.set("_noise_module_id", self._noise_module_id)
            logger.info(f"Noise suppression enabled (module {self._noise_module_id})")
        except subprocess.CalledProcessError as e:
            logger.error(f"enable_noise_suppression: pactl error — {e.stderr}")
        except Exception as e:
            logger.error(f"enable_noise_suppression: {e}")

    def disable_noise_suppression(self):
        """Unload the echo-cancel module."""
        mod_id = self._noise_module_id or self.settings.get("_noise_module_id")
        if not mod_id:
            return
        try:
            subprocess.run(
                ["pactl", "unload-module", str(mod_id)],
                check=True, timeout=5, capture_output=True
            )
            self._noise_module_id = None
            self.settings.set("noise_suppression", False)
            self.settings.set("_noise_module_id", None)
            logger.info("Noise suppression disabled")
        except Exception as e:
            logger.error(f"disable_noise_suppression: {e}")

    def is_noise_suppression_active(self) -> bool:
        """Check if the echo-cancel module is currently loaded."""
        return bool(self._noise_module_id or self.settings.get("_noise_module_id"))

    # ─── ALSA Mic Boost ──────────────────────────────────────────────────

    def get_available_alsa_controls(self) -> list[str]:
        """Return ALSA mixer controls relevant to mic input."""
        try:
            out = subprocess.check_output(["amixer", "scontrols"], text=True, timeout=5)
            return [
                line.strip() for line in out.splitlines()
                if any(k in line for k in ["Mic", "Capture", "Input", "Boost"])
            ]
        except Exception:
            return []

    def set_mic_boost(self, level: int):
        """
        Set ALSA Mic Boost hardware pre-amp level.
        level: 0–3 typical (hardware dependent, may not exist on all cards).
        """
        try:
            subprocess.run(
                ["amixer", "sset", "Mic Boost", str(level)],
                check=True, timeout=3, capture_output=True
            )
            self.settings.set("mic_boost", level)
            logger.info(f"ALSA Mic Boost → {level}")
        except subprocess.CalledProcessError:
            logger.warning("Mic Boost ALSA control not available on this hardware")
        except Exception as e:
            logger.error(f"set_mic_boost: {e}")

    # ─── Auto-Calibrate ──────────────────────────────────────────────────

    def auto_calibrate(self, duration_s: float = 3.0) -> dict:
        """
        Record <duration_s> seconds of ambient silence, measure the noise
        floor, and return recommended settings.

        Returns:
            {
                "noise_floor": float,           # RMS of ambient noise
                "recommended_threshold": int,   # silence_threshold setting
                "recommended_volume": int,      # mic volume % suggestion
            }
        """
        import numpy as np
        from .audio import AudioCapture

        audio = AudioCapture()
        samples: list[float] = []

        try:
            audio.start()
            deadline = time.time() + duration_s
            while time.time() < deadline:
                data = audio.get_data()
                if data:
                    arr = np.frombuffer(data, dtype=np.int16)
                    rms = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
                    samples.append(rms)
                else:
                    time.sleep(0.01)
        finally:
            audio.stop()

        if not samples:
            return {}

        noise_floor = float(np.percentile(samples, 95))   # 95th pct = reliable floor
        recommended_threshold = max(100, int(noise_floor * 1.5))

        # If floor is very low (<100 RMS), suggest a small volume boost
        recommended_volume = 100
        if noise_floor < 80:
            recommended_volume = 120

        logger.info(
            f"Auto-calibrate: floor={noise_floor:.0f} → "
            f"threshold={recommended_threshold}, volume={recommended_volume}%"
        )
        return {
            "noise_floor": noise_floor,
            "recommended_threshold": recommended_threshold,
            "recommended_volume": recommended_volume,
        }

    # ─── Restore on Startup ─────────────────────────────────────────────

    def restore_settings(self):
        """Re-apply saved enhancement settings on app startup."""
        vol = self.settings.get("mic_volume", 100)
        if vol != 100:
            self.set_input_volume(vol)

        if self.settings.get("noise_suppression", False):
            self.enable_noise_suppression()

        boost = self.settings.get("mic_boost")
        if boost is not None and boost > 0:
            self.set_mic_boost(boost)

    # ─── Internal ────────────────────────────────────────────────────────

    def _source(self) -> str:
        """Return the PulseAudio source to operate on."""
        return self.settings.get("audio_device", "@DEFAULT_SOURCE@")
