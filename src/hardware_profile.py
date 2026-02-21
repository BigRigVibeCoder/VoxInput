"""
HardwareProfile — Runtime hardware detection for VoxInput. (Phase 2 / Phase 3)

Detects available CPU cores, RAM, GPU (CUDA/ROCm), and VRAM at startup,
and recommends optimal compute settings for Vosk and Whisper engines.

DO NOT hardcode assumptions — always probe at runtime so this works
correctly across machines (CI servers, Raspberry Pi, workstations, laptops).

Cached at process startup — re-detection requires process restart.
"""
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class HardwareProfile:
    """
    Singleton hardware capability snapshot.

    Usage:
        profile = HardwareProfile.detect()
        logger.info(profile.whisper_device)   # "cuda" or "cpu"
        logger.info(profile.whisper_compute)  # "float16", "int8", etc.
        logger.info(profile.summary())
    """

    _instance: "HardwareProfile | None" = None

    def __init__(self):
        # ── CPU ─────────────────────────────────────────────
        self.cpu_cores_physical: int = os.cpu_count() or 1
        try:
            import psutil
            self.cpu_cores_physical = psutil.cpu_count(logical=False) or self.cpu_cores_physical
        except ImportError:
            pass
        self.cpu_cores_logical: int = os.cpu_count() or 1

        # ── RAM ─────────────────────────────────────────────
        self.ram_total_gb: float = 0.0
        self.ram_available_gb: float = 0.0
        try:
            import psutil
            mem = psutil.virtual_memory()
            self.ram_total_gb    = mem.total    / 1024**3
            self.ram_available_gb= mem.available/ 1024**3
        except ImportError:
            # Fallback: parse /proc/meminfo
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            self.ram_total_gb = int(line.split()[1]) / 1024**2
                        elif line.startswith("MemAvailable"):
                            self.ram_available_gb = int(line.split()[1]) / 1024**2
            except Exception:
                pass

        # ── GPU / CUDA ───────────────────────────────────────
        self.cuda_available:    bool  = False
        self.cuda_device_name:  str   = ""
        self.cuda_vram_total_gb:float = 0.0
        self.cuda_vram_free_gb: float = 0.0
        self.cuda_capability:   tuple = (0, 0)

        try:
            import torch
            if torch.cuda.is_available():
                self.cuda_available = True
                idx = torch.cuda.current_device()
                self.cuda_device_name = torch.cuda.get_device_name(idx)
                props = torch.cuda.get_device_properties(idx)
                self.cuda_vram_total_gb  = props.total_memory / 1024**3
                self.cuda_capability     = (props.major, props.minor)
                # Free VRAM (subtract PyTorch reserved)
                reserved = torch.cuda.memory_reserved(idx)
                self.cuda_vram_free_gb = (props.total_memory - reserved) / 1024**3
        except ImportError:
            # torch not installed — try nvidia-smi as fallback
            try:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                     "--format=csv,noheader,nounits"],
                    text=True, timeout=5
                )
                parts = [p.strip() for p in out.strip().split(",")]
                if len(parts) >= 3:
                    self.cuda_device_name   = parts[0]
                    self.cuda_vram_total_gb = int(parts[1]) / 1024
                    self.cuda_vram_free_gb  = int(parts[2]) / 1024
                    self.cuda_available     = True
            except Exception:
                pass

        # ── Derived Recommendations ──────────────────────────
        self.whisper_device, self.whisper_compute = self._pick_whisper_backend()
        self.vosk_chunk_ms = self._pick_vosk_chunk()

    # ─── Detection Logic ─────────────────────────────────────────────────

    def _pick_whisper_backend(self) -> tuple[str, str]:
        """
        Choose the best device + compute_type for faster-whisper.

        Rules (in priority order):
          CUDA ≥ 4GB free  → cuda / float16   (fast, full precision)
          CUDA ≥ 2GB free  → cuda / int8      (VRAM-constrained, still fast)
          CUDA <  2GB free → cpu  / int8      (VRAM too fragmented for Whisper)
          No CUDA          → cpu  / int8      (pure-CPU best option)
        """
        if self.cuda_available:
            if self.cuda_vram_free_gb >= 4.0:
                return ("cuda", "float16")
            elif self.cuda_vram_free_gb >= 2.0:
                return ("cuda", "int8")
            else:
                logger.info(
                    f"GPU VRAM too fragmented ({self.cuda_vram_free_gb:.1f}GB free) "
                    "— using CPU for Whisper to avoid OOM"
                )
                return ("cpu", "int8")
        return ("cpu", "int8")

    def _pick_vosk_chunk(self) -> int:
        """
        Choose Vosk audio chunk size in milliseconds.

        More CPU cores = smaller chunks = lower latency.
        """
        if self.cpu_cores_logical >= 8:
            return 100    # 100ms — full real-time feel
        elif self.cpu_cores_logical >= 4:
            return 150    # 150ms — reasonable on quad-core
        else:
            return 200    # 200ms — safe fallback for slow CPUs

    # ─── Summary ─────────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = [
            "─── VoxInput Hardware Profile ───",
            f"  CPU : {self.cpu_cores_physical}P/{self.cpu_cores_logical}L cores",
            f"  RAM : {self.ram_total_gb:.0f}GB total, {self.ram_available_gb:.0f}GB free",
        ]
        if self.cuda_available:
            lines += [
                f"  GPU : {self.cuda_device_name}",
                f"  VRAM: {self.cuda_vram_total_gb:.0f}GB total, {self.cuda_vram_free_gb:.1f}GB free",
                f"  CUDA: capability {self.cuda_capability[0]}.{self.cuda_capability[1]}",
            ]
        else:
            lines.append("  GPU : None (CUDA unavailable)")
        lines += [
            f"  ↳ Whisper backend: {self.whisper_device} / {self.whisper_compute}",
            f"  ↳ Vosk chunk:      {self.vosk_chunk_ms}ms",
        ]
        return "\n".join(lines)

    # ─── Singleton ───────────────────────────────────────────────────────

    @classmethod
    def detect(cls) -> "HardwareProfile":
        """Return the cached profile (or detect on first call)."""
        if cls._instance is None:
            cls._instance = cls()
            logger.info(cls._instance.summary())
        return cls._instance

    @classmethod
    def reset(cls):
        """Force re-detection (primarily used in tests)."""
        cls._instance = None
