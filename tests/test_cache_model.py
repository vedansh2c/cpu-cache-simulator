import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    compiler = shutil.which("c++")
    if not compiler:
        pytest.skip("C++ compiler unavailable")
    binary = tmp_path_factory.mktemp("cache") / "model"
    source = Path(__file__).resolve().parents[1] / "cache_model/cache_model.cpp"
    subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            "-O2",
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
    )
    return binary


@pytest.mark.parametrize(
    ("capacity", "ways", "addresses", "hits", "misses"),
    [
        (128, 1, [0, 8, 64, 72], 2, 2),  # Spatial locality within a cache line.
        (128, 1, [0, 128, 0], 0, 3),  # Direct-map conflict.
        (128, 2, [0, 128, 0], 1, 2),  # Two ways resolve the conflict.
        (128, 2, [0, 64, 0, 128, 64], 1, 4),  # LRU must evict 64, not recently used 0.
        (128, 2, [0, 64, 128, 0], 0, 4),  # Capacity misses.
        (256, 2, [0, 64, 128, 0], 1, 3),
    ],
)
def test_hand_calculated_traces(tmp_path, model, capacity, ways, addresses, hits, misses):
    trace = tmp_path / "trace.txt"
    trace.write_text("\n".join(hex(a) for a in addresses))
    output = subprocess.check_output([str(model), str(capacity), "64", str(ways), str(trace)])
    result = json.loads(output)
    assert result["hits"] == hits and result["misses"] == misses


def test_invalid_geometry(tmp_path, model):
    trace = tmp_path / "trace.txt"
    trace.write_text("0\n64\n0\n")
    for geometry in [(0, 64, 2), (128, 0, 2), (128, 64, 3), (128, 64, 8)]:
        result = subprocess.run([str(model), *map(str, geometry), str(trace)], capture_output=True)
        assert result.returncode == 2


def test_empty_trace_and_malformed_input(tmp_path, model):
    trace = tmp_path / "trace.txt"
    trace.write_text("")
    result = json.loads(subprocess.check_output([str(model), "128", "64", "2", str(trace)]))
    assert result["miss_rate"] is None
    trace.write_text("-1\n")
    assert (
        subprocess.run([str(model), "128", "64", "2", str(trace)], capture_output=True).returncode
        == 2
    )
