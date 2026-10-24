from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Architecture(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(default="Timing baseline", min_length=1, max_length=80)
    cpu_model: Literal["TimingSimpleCPU", "O3CPU"] = "TimingSimpleCPU"
    cores: Literal[1] = 1
    clock_mhz: int = Field(default=2000, ge=100, le=4000)
    l1i_kib: int = Field(default=32, ge=4, le=128)
    l1d_kib: int = Field(default=32, ge=4, le=128)
    l2_kib: int = Field(default=256, ge=128, le=8192)
    l1_assoc: Literal[1, 2, 4, 8] = 2
    l2_assoc: Literal[1, 2, 4, 8, 16] = 8
    line_bytes: Literal[32, 64, 128] = 64
    l1_latency_cycles: int = Field(default=2, ge=1, le=20)
    l2_latency_cycles: int = Field(default=20, ge=1, le=100)
    memory_mib: Literal[128, 256, 512, 1024, 2048] = 512
    memory_model: Literal["DDR3_1600_8x8"] = "DDR3_1600_8x8"

    @field_validator("cores", "l1_assoc", "l2_assoc", "line_bytes", "memory_mib", mode="before")
    @classmethod
    def strict_integer_choices(cls, value):
        if type(value) is not int:
            raise ValueError("Expected an integer choice")
        return value

    @model_validator(mode="after")
    def cache_geometry(self):
        for size, assoc in [
            (self.l1i_kib, self.l1_assoc),
            (self.l1d_kib, self.l1_assoc),
            (self.l2_kib, self.l2_assoc),
        ]:
            sets = size * 1024 // (assoc * self.line_bytes)
            if size & (size - 1) or sets < 1 or sets & (sets - 1):
                raise ValueError("Caches require power-of-two capacities and set counts")
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    configuration_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    benchmark: Literal["matrix", "sequential", "random", "traversal", "sorting", "pointer"] = (
        "matrix"
    )
    size: int = Field(default=32, ge=2, le=262144)

    @model_validator(mode="after")
    def workload_size(self):
        if self.benchmark == "matrix" and self.size > 128:
            raise ValueError("Matrix dimension must be 2..128")
        return self


class SweepRequest(SimulationRequest):
    l1d_kib: list[int] = Field(default_factory=lambda: [16, 32, 64], min_length=1, max_length=4)
    l2_kib: list[int] = Field(default_factory=lambda: [256, 512], min_length=1, max_length=4)
    l1_assoc: list[int] = Field(default_factory=lambda: [2, 4], min_length=1, max_length=4)


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    simulation_ids: list[str] = Field(min_length=2, max_length=64)
    max_cache_kib: int | None = Field(default=None, ge=1)
