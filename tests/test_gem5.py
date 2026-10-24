import os
from dataclasses import replace
from types import SimpleNamespace

import pytest
from app.runner import run_simulation, simulator_version
from app.schemas import Architecture
from app.settings import Settings


@pytest.mark.gem5
def test_real_gem5_matrix(tmp_path):
    if os.getenv("RUN_GEM5_TESTS") != "1":
        pytest.skip("Opt in with RUN_GEM5_TESTS=1 and provide GEM5_BINARY / MATRIX_BINARY")
    settings = replace(Settings(), data_dir=tmp_path)
    version = simulator_version(settings.gem5)
    run = SimpleNamespace(
        id="b" * 32, architecture=Architecture().model_dump(), size=8, benchmark="matrix"
    )
    metrics, _ = run_simulation(settings, run, lambda: False, version)
    values = metrics["values"]
    assert values["cycles"]["value"] > 0
    assert 0 < values["ipc"]["value"] <= 1.01
    for cache in ("l1i", "l1d", "l2"):
        assert 0 <= values[f"{cache}_miss_rate"]["value"] <= 1
