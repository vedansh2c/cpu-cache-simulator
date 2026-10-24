import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import time
from pathlib import Path

from app.metrics import extract_metrics
from app.schemas import Architecture
from app.settings import GEM5_COMMIT, GEM5_VERSION, Settings


class Cancelled(Exception):
    pass


def simulator_version(binary: str) -> str:
    result = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, timeout=15, check=True
    )
    if not re.search(rf"\bgem5 version {re.escape(GEM5_VERSION)}\b", result.stdout):
        raise RuntimeError(f"Expected gem5 {GEM5_VERSION}; got {result.stdout[:200]}")
    return GEM5_VERSION


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def terminate(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            process.wait()
            return
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def run_simulation(settings: Settings, run, is_cancelled, version: str):
    architecture = Architecture.model_validate(run.architecture)
    directory = settings.data_dir / "runs" / run.id
    directory.mkdir(parents=True, exist_ok=False)
    config_path = directory / "architecture.json"
    config_path.write_text(architecture.model_dump_json(indent=2))
    benchmark = settings.benchmark if run.benchmark == "matrix" else settings.memory_benchmark
    command = [
        settings.gem5,
        f"--outdir={directory}",
        str(settings.script),
        "--config",
        str(config_path),
        "--binary",
        str(benchmark),
        "--benchmark",
        run.benchmark,
        "--size",
        str(run.size),
        "--max-ticks",
        str(settings.max_ticks),
    ]
    metadata = {
        "gem5_version": version,
        "gem5_commit": GEM5_COMMIT,
        "simulator_host_architecture": platform.machine(),
        "command": command,
        "workload_sha256": digest(benchmark),
        "script_sha256": digest(settings.script),
        "size": run.size,
        "max_ticks": settings.max_ticks,
        "timeout_seconds": settings.timeout,
    }
    (directory / "manifest.json").write_text(json.dumps(metadata, indent=2))
    started = time.monotonic()
    log_path = directory / "simulation.log"

    def check_output_budget():
        output_bytes = sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
        if output_bytes > settings.max_log_bytes:
            raise RuntimeError("Simulation output size limit exceeded")

    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, cwd=directory
        )
        try:
            while process.poll() is None:
                if is_cancelled():
                    raise Cancelled("Simulation cancelled")
                if time.monotonic() - started > settings.timeout:
                    raise TimeoutError("Host simulation timeout exceeded")
                check_output_budget()
                time.sleep(0.1)
            if is_cancelled():
                raise Cancelled("Simulation cancelled")
            if process.returncode:
                raise RuntimeError(f"gem5 exited with code {process.returncode}; inspect logs")
        finally:
            terminate(process)
    check_output_budget()
    exit_info = json.loads((directory / "exit.json").read_text())
    if exit_info["cause"] != "exiting with last active thread context" or exit_info["code"] != 0:
        raise RuntimeError(f"Workload did not finish successfully: {exit_info}")
    # Closed-form checksum, independently evaluated again outside the simulated program.
    n = run.size
    s1, s2 = n * (n - 1) // 2, n * (n - 1) * (2 * n - 1) // 6
    if run.benchmark == "matrix":
        expected = sum(
            2 * s2 + (2 * (i + 1) + j + 1) * s1 + n * (i + 1) * (j + 1)
            for i in range(n)
            for j in range(n)
        )
    else:
        expected = n * (n + 1) // 2 if run.benchmark == "sorting" else n * (n - 1) // 2
    output = (directory / "workload.stdout").read_text()
    marker = "MATRIX_OK" if run.benchmark == "matrix" else f"BENCHMARK_OK {run.benchmark}"
    if output.strip() != f"{marker} n={n} checksum={expected}":
        raise RuntimeError("Missing or incorrect benchmark correctness marker")
    metrics = extract_metrics((directory / "stats.txt").read_text(), version)
    for key in ("cycles", "instructions", "simulated_seconds"):
        value = metrics["values"][key]["value"]
        if value is None or value <= 0:
            raise RuntimeError(f"Required performance counter missing or invalid: {key}")
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False))
    return metrics, time.monotonic() - started
