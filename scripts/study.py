"""Reproducible measured study: six workloads, two architectures, one tiny sweep."""

import argparse
import json
import time
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--output", default="build/study.json")
    args = parser.parse_args()

    def request(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            args.url + "/api" + path, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)

    def wait(id):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            run = request(f"/simulations/{id}")
            if run["status"] == "completed":
                return run
            if run["status"] in ("failed", "cancelled"):
                raise RuntimeError(f"Run {id}: {run['error']}")
            time.sleep(0.5)
        raise TimeoutError(f"Run {id} did not finish")

    if not request("/health")["worker_ready"]:
        raise SystemExit("Worker is not ready")
    baseline = json.loads(
        (Path(__file__).resolve().parents[1] / "examples/baseline.json").read_text()
    )
    configs = [
        request(
            "/configurations",
            {**baseline, "name": "Study / small caches", "l1d_kib": 16, "l2_kib": 256},
        ),
        request(
            "/configurations",
            {**baseline, "name": "Study / larger caches", "l1d_kib": 64, "l2_kib": 512},
        ),
    ]
    runs, comparisons = [], []
    for benchmark in ("matrix", "sequential", "random", "traversal", "sorting", "pointer"):
        cohort = []
        for config in configs:
            run = request(
                "/simulations",
                {
                    "configuration_id": config["id"],
                    "benchmark": benchmark,
                    "size": 32 if benchmark == "matrix" else 4096,
                },
            )
            run = wait(run["id"])
            cohort.append(run["id"])
            runs.append(run)
            print(
                f"Validated {benchmark} / {config['architecture']['name']}: {run['id']}", flush=True
            )
        comparisons.append(request("/experiments/compare", {"simulation_ids": cohort}))
    experiment = request(
        "/experiments/sweep",
        {
            "configuration_id": configs[0]["id"],
            "benchmark": "matrix",
            "size": 32,
            "l1d_kib": [16, 32],
            "l2_kib": [256],
            "l1_assoc": [2],
        },
    )
    results = request(f"/experiments/{experiment['id']}/results")
    for run in results["runs"]:
        wait(run["id"])
    results = request(f"/experiments/{experiment['id']}/results")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "measurement_scope": "whole_process_SE",
                "gem5_version": request("/health")["gem5_version"],
                "runs": runs,
                "comparisons": comparisons,
                "sweep": results,
            },
            indent=2,
            allow_nan=False,
        )
    )
    print(f"Measured study written to {output}")


if __name__ == "__main__":
    main()
