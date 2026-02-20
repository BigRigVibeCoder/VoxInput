"""tests/unit/test_hardware_profile.py — Unit tests for HardwareProfile."""
import sys
sys.path.insert(0, ".")


class TestHardwareProfileDetect:
    """HardwareProfile.detect() must return a profile with valid attributes."""

    def setup_method(self):
        from src.hardware_profile import HardwareProfile
        self.profile = HardwareProfile.detect()

    def test_detect_returns_profile(self):
        assert self.profile is not None

    def test_whisper_device_valid(self):
        assert self.profile.whisper_device in ("cpu", "cuda")

    def test_compute_type_valid(self):
        assert self.profile.whisper_compute in (
            "int8", "float16", "float32", "int8_float16"
        )

    def test_vosk_chunk_positive(self):
        assert self.profile.vosk_chunk_ms > 0

    def test_cpu_cores_logical_detected(self):
        assert self.profile.cpu_cores_logical >= 1

    def test_ram_total_positive(self):
        assert self.profile.ram_total_gb > 0.0

    def test_cuda_available_is_bool(self):
        assert isinstance(self.profile.cuda_available, bool)

    def test_no_cuda_uses_cpu_device(self):
        """If cuda_available is False the device should be 'cpu'."""
        if not self.profile.cuda_available:
            assert self.profile.whisper_device == "cpu"
