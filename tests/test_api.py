from concurrent.futures import ThreadPoolExecutor

import pytest
from app.db import Configuration, Simulation, database
from app.main import create_app
from app.schemas import Architecture
from app.settings import Settings
from app.worker import claim
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        yield client


def test_api_lifecycle_and_persistence(client, tmp_path):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["worker_ready"] is False
    config = client.post("/api/configurations", json={}).json()
    assert config["architecture"]["l1d_kib"] == 32
    run = client.post("/api/simulations", json={"configuration_id": config["id"]})
    assert run.status_code == 202
    run_id = run.json()["id"]
    assert client.get(f"/api/simulations/{run_id}").json()["status"] == "queued"
    assert client.get(f"/api/simulations/{run_id}/metrics").status_code == 409
    assert client.get(f"/api/simulations/{run_id}/logs").json()["simulation.log"]["text"] == ""
    assert client.post(f"/api/simulations/{run_id}/cancel").status_code == 202
    assert client.post(f"/api/simulations/{run_id}/cancel").status_code == 409
    with TestClient(create_app(Settings(data_dir=tmp_path))) as restarted:
        assert restarted.get("/api/configurations").json()[0]["id"] == config["id"]
        assert restarted.get("/api/simulations").json()[0]["status"] == "cancelled"


@pytest.mark.parametrize(
    "payload",
    [
        {"cpu_model": "UnknownCPU"},
        {"cores": 2},
        {"l1d_kib": 33},
        {"line_bytes": 48},
        {"memory_model": "unknown"},
        {"clock_mhz": "2000"},
        {"cores": True},
        {"line_bytes": 64.0},
        {"evil": "x"},
    ],
)
def test_config_validation(client, payload):
    assert client.post("/api/configurations", json=payload).status_code == 422


def test_bad_requests(client):
    assert client.get("/api/simulations/not-a-uuid/logs").status_code == 404
    assert client.get("/api/simulations/" + "a" * 32).status_code == 404
    assert client.post("/api/simulations", json={"configuration_id": "a" * 32}).status_code == 404
    config = client.post("/api/configurations", json={}).json()
    for extra in ({"size": 129}, {"size": True}, {"benchmark": "unknown"}, {"command": "sh"}):
        assert (
            client.post(
                "/api/simulations", json={"configuration_id": config["id"], **extra}
            ).status_code
            == 422
        )


def test_claim_is_atomic(tmp_path):
    sessions = database(tmp_path)
    with sessions() as session:
        config = Configuration(architecture=Architecture().model_dump())
        session.add(config)
        session.flush()
        session.add(
            Simulation(
                configuration_id=config.id,
                architecture=config.architecture,
                benchmark="matrix",
                size=8,
            )
        )
        session.commit()
    with ThreadPoolExecutor(4) as pool:
        claims = list(pool.map(lambda _: claim(sessions), range(4)))
    assert len([run for run in claims if run]) == 1


def test_queue_limit(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path, max_queue=1))) as client:
        config = client.post("/api/configurations", json={}).json()
        payload = {"configuration_id": config["id"]}
        assert client.post("/api/simulations", json=payload).status_code == 202
        assert client.post("/api/simulations", json=payload).status_code == 429


def test_artifact_download_allowlist(client, tmp_path):
    config = client.post("/api/configurations", json={}).json()
    run = client.post("/api/simulations", json={"configuration_id": config["id"]}).json()
    directory = tmp_path / "runs" / run["id"]
    directory.mkdir(parents=True)
    (directory / "stats.txt").write_text("test artifact, not measured statistics")
    (directory / "private.txt").write_text("not an exposed artifact")
    base = f"/api/simulations/{run['id']}/artifacts"
    assert client.get(base + "/stats.txt").text == "test artifact, not measured statistics"
    assert client.get(base + "/private.txt").status_code == 404
    assert client.get(base + "/metrics.json").status_code == 404
