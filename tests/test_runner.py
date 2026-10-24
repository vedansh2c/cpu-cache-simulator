import json
import sys
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest
from app.db import Configuration, Simulation, database
from app.runner import Cancelled, run_simulation
from app.schemas import Architecture
from app.settings import GEM5_VERSION, Settings
from app.worker import claim, execute


def setup_process(tmp_path, stats_text, mode="success"):
    # A real child process exercises orchestration; it is explicitly a test double,
    # not gem5. Real simulator coverage lives in test_gem5.py and the smoke script.
    fake = tmp_path / "process.py"
    fake.write_text(f"""import json, pathlib, sys, time
directory = pathlib.Path(sys.argv[1].split("=", 1)[1])
mode = {mode!r}
if mode == "failure": sys.exit(7)
if mode == "sleep": time.sleep(30)
if mode == "large":
    print("x" * 20000, flush=True)
    time.sleep(30)
(directory / "exit.json").write_text(json.dumps({{
    "cause": "exiting with last active thread context", "code": 0}}))
(directory / "workload.stdout").write_text("MATRIX_OK n=2 checksum=44\\n")
(directory / "stats.txt").write_text({stats_text!r})
""")
    wrapper = tmp_path / "fake-gem5"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
    wrapper.chmod(0o755)
    benchmark = tmp_path / "matrix"
    benchmark.write_bytes(b"test-only workload identity")
    settings = Settings(
        data_dir=tmp_path / "data", gem5=str(wrapper), script=fake, benchmark=benchmark, timeout=1
    )
    run = SimpleNamespace(
        id="a" * 32, architecture=Architecture().model_dump(), size=2, benchmark="matrix"
    )
    return settings, run


def test_success_persists_provenance(tmp_path, stats_text):
    settings, run = setup_process(tmp_path, stats_text)
    metrics, elapsed = run_simulation(settings, run, lambda: False, GEM5_VERSION)
    assert metrics["values"]["ipc"]["value"] == 0.25
    assert elapsed > 0
    manifest = json.loads((settings.data_dir / "runs" / run.id / "manifest.json").read_text())
    assert len(manifest["workload_sha256"]) == 64
    assert manifest["gem5_version"] == GEM5_VERSION


@pytest.mark.parametrize(
    ("mode", "exception"),
    [("failure", RuntimeError), ("sleep", TimeoutError), ("large", RuntimeError)],
)
def test_process_errors(tmp_path, stats_text, mode, exception):
    settings, run = setup_process(tmp_path, stats_text, mode)
    if mode == "large":
        settings = replace(settings, max_log_bytes=10000)
    with pytest.raises(exception):
        run_simulation(settings, run, lambda: False, GEM5_VERSION)


def test_cancel_kills_process(tmp_path, stats_text):
    settings, run = setup_process(tmp_path, stats_text, "sleep")
    with pytest.raises(Cancelled):
        run_simulation(settings, run, lambda: True, GEM5_VERSION)


@pytest.mark.parametrize("mode", ["success", "failure"])
def test_worker_records_terminal_status_and_continues(tmp_path, stats_text, mode):
    settings, _ = setup_process(tmp_path, stats_text, mode)
    sessions = database(settings.data_dir)
    with sessions() as session:
        config = Configuration(architecture=Architecture().model_dump())
        session.add(config)
        session.flush()
        for _ in range(2):
            session.add(
                Simulation(
                    configuration_id=config.id,
                    architecture=config.architecture,
                    size=2,
                    benchmark="matrix",
                )
            )
        session.commit()
    for _ in range(2):
        run = claim(sessions)
        execute(settings, sessions, run, threading.Event(), GEM5_VERSION)
        with sessions() as session:
            saved = session.get(Simulation, run.id)
            if mode == "failure":
                assert saved.status == "failed"
                assert "code 7" in saved.error
                assert saved.metrics is None
            else:
                assert saved.status == "completed"
                assert saved.metrics["values"]["cycles"]["value"] == 4000
                assert saved.wall_seconds > 0
            assert saved.finished_at
    assert claim(sessions) is None
