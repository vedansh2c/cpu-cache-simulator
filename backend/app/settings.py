import os
from dataclasses import dataclass
from pathlib import Path

GEM5_VERSION = "25.1.0.1"
GEM5_COMMIT = "c8222cc67a399bfc01e8658dd14b30d5bfd634f9"
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
    gem5: str = os.getenv("GEM5_BINARY", "/opt/gem5/build/X86/gem5.opt")
    script: Path = Path(os.getenv("GEM5_SCRIPT", str(ROOT / "simulation/se.py")))
    benchmark: Path = Path(os.getenv("MATRIX_BINARY", "/opt/workloads/matrix"))
    memory_benchmark: Path = Path(os.getenv("MEMORY_BINARY", "/opt/workloads/memory"))
    concurrency: int = int(os.getenv("WORKER_CONCURRENCY", "1"))
    timeout: float = float(os.getenv("SIMULATION_TIMEOUT_SECONDS", "120"))
    max_log_bytes: int = 8 * 1024 * 1024
    max_queue: int = 100
    max_ticks: int = 10_000_000_000  # 10 ms at the explicit 1 THz tick frequency.

    def __post_init__(self):
        if not 1 <= self.concurrency <= 4 or not 1 <= self.timeout <= 3600:
            raise ValueError("Concurrency must be 1..4; timeout must be 1..3600 seconds")
