"""Real HTTP -> durable queue -> gem5 -> parsed metrics acceptance check.

Uses only Python's standard library. Does not fabricate or inject any statistics.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--size", type=int, default=8)
    parser.add_argument("--cpu", choices=["TimingSimpleCPU", "O3CPU"], default="TimingSimpleCPU")
    parser.add_argument("--memory-mib", choices=[128, 256, 512, 1024, 2048], type=int, default=512)
    parser.add_argument(
        "--benchmark",
        default="matrix",
        choices=["matrix", "sequential", "random", "traversal", "sorting", "pointer"],
    )
    parser.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()

    def request(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            args.url + path, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)

    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            if request("/api/health")["worker_ready"]:
                break
        except (OSError, urllib.error.URLError):
            pass
        if time.monotonic() >= deadline:
            raise SystemExit("Worker did not become ready")
        time.sleep(1)
    baseline = Path(__file__).resolve().parents[1] / "examples/baseline.json"
    config = request(
        "/api/configurations",
        {**json.loads(baseline.read_text()), "cpu_model": args.cpu, "memory_mib": args.memory_mib},
    )
    run = request(
        "/api/simulations",
        {"configuration_id": config["id"], "size": args.size, "benchmark": args.benchmark},
    )
    print(f"Simulation {run['id']} queued", flush=True)
    deadline = time.monotonic() + args.wait_seconds
    path = f"/api/simulations/{run['id']}"
    while True:
        run = request(path)
        if run["status"] == "completed":
            metrics = request(path + "/metrics")
            values = metrics["values"]
            assert values["cycles"]["value"] > 0
            assert values["instructions"]["value"] > 0
            assert values["ipc"]["value"] > 0
            if args.cpu == "TimingSimpleCPU":
                assert values["ipc"]["value"] <= 1.01
            for cache in ("l1i", "l1d", "l2"):
                assert 0 <= values[f"{cache}_miss_rate"]["value"] <= 1
            print(
                json.dumps(
                    {"id": run["id"], "status": run["status"], "metrics": metrics},
                    indent=2,
                    allow_nan=False,
                )
            )
            return
        if run["status"] in ("failed", "cancelled"):
            print(json.dumps(request(path + "/logs"), indent=2))
            raise SystemExit(f"Simulation {run['status']}: {run['error']}")
        if time.monotonic() >= deadline:
            raise SystemExit(f"Timed out waiting for {run['id']}; last status={run['status']}")
        time.sleep(1)


if __name__ == "__main__":
    main()
