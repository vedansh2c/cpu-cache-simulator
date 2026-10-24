from types import SimpleNamespace

import pytest
from app.analysis import compare
from app.main import create_app
from app.schemas import Architecture
from app.settings import Settings
from fastapi.testclient import TestClient


def test_sweep_atomic_validation_and_tracking(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        config = client.post("/api/configurations", json={}).json()
        body = {
            "configuration_id": config["id"],
            "l1d_kib": [16, 32],
            "l2_kib": [256],
            "l1_assoc": [2],
            "benchmark": "pointer",
            "size": 32,
        }
        response = client.post("/api/experiments/sweep", json={**body, "l1d_kib": [16, 33]})
        assert response.status_code == 422
        assert client.get("/api/simulations").json() == []
        response = client.post("/api/experiments/sweep", json=body)
        assert response.status_code == 202
        results = client.get(f"/api/experiments/{response.json()['id']}/results").json()
        assert results["total"] == 2 and results["finished"] == 0
        assert results["counts"] == {"queued": 2}
        ids = [r["id"] for r in results["runs"]]
        assert (
            client.post("/api/experiments/compare", json={"simulation_ids": ids}).status_code == 422
        )


def measured(id, cycles, capacity, ipc=1):
    return SimpleNamespace(
        id=id,
        status="completed",
        benchmark="matrix",
        size=8,
        architecture={**Architecture().model_dump(), "l2_kib": capacity},
        metrics={
            "values": {
                "cycles": {"value": cycles, "unit": "cycles"},
                "ipc": {"value": ipc, "unit": "instructions/cycle"},
            }
        },
    )


def test_pareto_constraints_and_nonmonotonic_capacity():
    a, b, c = measured("a", 100, 256), measured("b", 120, 512), measured("c", 90, 512)
    result = compare([a, b, c])
    assert result["pareto_ids"] == ["a", "c"]
    assert result["rows"][1]["metrics"]["cycles"]["percent"] == 20
    assert compare([a, c], 400)["pareto_ids"] == ["a"]


def test_missing_and_zero_comparison():
    result = compare([measured("a", 100, 256, 0), measured("b", 120, 512, None)])
    assert result["rows"][0]["metrics"]["ipc"]["percent"] is None
    assert result["rows"][1]["metrics"]["ipc"]["absolute"] is None
    b = measured("b", 100, 256)
    b.size = 16
    with pytest.raises(ValueError, match="identical benchmark"):
        compare([measured("a", 100, 256), b])
