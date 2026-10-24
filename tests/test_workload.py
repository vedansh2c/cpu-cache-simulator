import shutil
import subprocess
from pathlib import Path

import pytest


def test_native_workload_correctness(tmp_path):
    compiler = shutil.which("cc")
    if not compiler:
        pytest.skip("C compiler unavailable")
    source = Path(__file__).resolve().parents[1] / "workloads/matrix.c"
    binary = tmp_path / "matrix"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
    )
    for n in (2, 3, 8, 32, 128):
        result = subprocess.run([str(binary), str(n)], text=True, capture_output=True, check=True)
        # Independent scalar reference for the small case; all sizes validate in C.
        if n == 2:
            expected = sum(
                sum((i + k + 1) * (2 * k + j + 1) for k in range(n))
                for i in range(n)
                for j in range(n)
            )
            assert result.stdout == f"MATRIX_OK n=2 checksum={expected}\n"
        assert f"MATRIX_OK n={n}" in result.stdout
    for args in ([], ["0"], ["129"], ["3x"], [""], ["9999999999999999999999999999999"]):
        assert subprocess.run([str(binary), *args], capture_output=True).returncode == 2


def test_memory_workload_correctness(tmp_path):
    compiler = shutil.which("cc")
    if not compiler:
        pytest.skip("C compiler unavailable")
    binary = tmp_path / "memory"
    source = Path(__file__).resolve().parents[1] / "workloads/memory.c"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
    )
    for name in ("sequential", "random", "traversal", "sorting", "pointer"):
        for n in (2, 67, 4096):
            result = subprocess.run(
                [str(binary), name, str(n)], check=True, capture_output=True, text=True
            )
            expected = n * (n + 1) // 2 if name == "sorting" else n * (n - 1) // 2
            assert result.stdout == f"BENCHMARK_OK {name} n={n} checksum={expected}\n"
