import json
import time
from collections import Counter
from contextlib import asynccontextmanager
from itertools import product
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text

from app.analysis import compare
from app.db import Configuration, Experiment, Simulation, database, now
from app.schemas import Architecture, CompareRequest, SimulationRequest, SweepRequest
from app.settings import GEM5_VERSION, Settings


def create_app(settings: Settings | None = None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.sessions = database(settings.data_dir)
        yield
        app.state.sessions.kw["bind"].dispose()

    app = FastAPI(title="CPU Cache & Memory Performance Platform", lifespan=lifespan)

    def fetch(session, model, id):
        try:
            if UUID(id).hex != id:
                raise ValueError()
        except ValueError:
            raise HTTPException(404, "Not found") from None
        record = session.get(model, id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    def serialize(record):
        return {column.name: getattr(record, column.name) for column in record.__table__.columns}

    @app.get("/api/health")
    def health():
        with app.state.sessions() as session:
            session.execute(text("SELECT 1"))
        try:
            worker = json.loads((settings.data_dir / "worker.json").read_text())
            ready = 0 <= time.time() - worker["timestamp"] < 10
        except (OSError, ValueError, KeyError):
            ready = False
        return {
            "status": "ok",
            "worker_ready": ready,
            "gem5_version": GEM5_VERSION,
            "measurement_scope": "whole_process_SE",
        }

    @app.get("/api/benchmarks")
    def benchmarks():
        return [
            {
                "id": "matrix",
                "language": "C11",
                "size_unit": "matrix dimension",
                "min_size": 2,
                "max_size": 128,
                "default_size": 32,
                "scope": "whole process; initialization, multiplication and validation",
            }
        ] + [
            {
                "id": name,
                "language": "C11",
                "size_unit": "elements",
                "min_size": 2,
                "max_size": 262144,
                "default_size": 4096,
                "scope": "whole process including initialization and validation",
            }
            for name in ("sequential", "random", "traversal", "sorting", "pointer")
        ]

    @app.get("/api/configurations")
    def configurations():
        with app.state.sessions() as session:
            return [
                serialize(c)
                for c in session.scalars(select(Configuration).order_by(Configuration.created_at))
            ]

    @app.post("/api/configurations", status_code=201)
    def create_configuration(config: Architecture):
        with app.state.sessions() as session:
            record = Configuration(architecture=config.model_dump())
            session.add(record)
            session.commit()
            return serialize(record)

    @app.post("/api/simulations", status_code=202)
    def simulate(request: SimulationRequest):
        with app.state.sessions() as session:
            # Admission and insert share a write transaction, including concurrent HTTP requests.
            session.execute(text("BEGIN IMMEDIATE"))
            config = fetch(session, Configuration, request.configuration_id)
            count = session.scalar(
                select(func.count())
                .select_from(Simulation)
                .where(Simulation.status.in_(["queued", "running"]))
            )
            if count >= settings.max_queue:
                raise HTTPException(429, "Simulation queue is full")
            run = Simulation(
                configuration_id=config.id,
                architecture=config.architecture,
                benchmark=request.benchmark,
                size=request.size,
            )
            session.add(run)
            session.commit()
            return serialize(run)

    @app.get("/api/simulations")
    def history(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        with app.state.sessions() as session:
            return [
                serialize(r)
                for r in session.scalars(
                    select(Simulation)
                    .order_by(Simulation.created_at.desc(), Simulation.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]

    @app.get("/api/simulations/{id}")
    def simulation(id: str):
        with app.state.sessions() as session:
            return serialize(fetch(session, Simulation, id))

    @app.get("/api/simulations/{id}/metrics")
    def metrics(id: str):
        with app.state.sessions() as session:
            run = fetch(session, Simulation, id)
            if run.status != "completed":
                raise HTTPException(409, f"Metrics unavailable: simulation is {run.status}")
            return run.metrics

    @app.get("/api/simulations/{id}/logs")
    def logs(id: str, tail_bytes: int = Query(16000, ge=1, le=65536)):
        with app.state.sessions() as session:
            fetch(session, Simulation, id)
        directory = settings.data_dir / "runs" / id
        result = {}
        for name in ("simulation.log", "workload.stdout", "workload.stderr"):
            try:
                with (directory / name).open("rb") as stream:
                    stream.seek(0, 2)
                    length = stream.tell()
                    stream.seek(max(0, length - tail_bytes))
                    result[name] = {
                        "text": stream.read(tail_bytes).decode(errors="replace"),
                        "truncated": length > tail_bytes,
                    }
            except FileNotFoundError:
                result[name] = {"text": "", "truncated": False}
        return result

    @app.get("/api/simulations/{id}/artifacts/{name}")
    def artifact(id: str, name: str):
        with app.state.sessions() as session:
            fetch(session, Simulation, id)
        if name not in {
            "stats.txt",
            "config.ini",
            "config.json",
            "architecture.json",
            "manifest.json",
            "exit.json",
            "metrics.json",
        }:
            raise HTTPException(404, "Unknown artifact")
        path = settings.data_dir / "runs" / id / name
        if not path.is_file():
            raise HTTPException(404, "Artifact not yet available")
        return FileResponse(path, filename=name)

    @app.post("/api/simulations/{id}/cancel", status_code=202)
    def cancel(id: str):
        with app.state.sessions() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            run = fetch(session, Simulation, id)
            if run.status not in ("queued", "running"):
                raise HTTPException(409, "Simulation has already finished")
            run.status, run.finished_at = "cancelled", now()
            session.commit()
        return Response(status_code=202)

    @app.post("/api/experiments/sweep", status_code=202)
    def sweep(request: SweepRequest):
        with app.state.sessions() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            base = fetch(session, Configuration, request.configuration_id)
            combinations = list(
                product(
                    dict.fromkeys(request.l1d_kib),
                    dict.fromkeys(request.l2_kib),
                    dict.fromkeys(request.l1_assoc),
                )
            )
            architectures = []
            for l1, l2, assoc in combinations:
                try:
                    architectures.append(
                        Architecture.model_validate(
                            {**base.architecture, "l1d_kib": l1, "l2_kib": l2, "l1_assoc": assoc}
                        ).model_dump()
                    )
                except ValueError as error:
                    raise HTTPException(422, str(error)) from error
            count = session.scalar(
                select(func.count())
                .select_from(Simulation)
                .where(Simulation.status.in_(["queued", "running"]))
            )
            if count + len(architectures) > settings.max_queue:
                raise HTTPException(429, "Sweep exceeds available queue capacity")
            experiment = Experiment(definition=request.model_dump())
            session.add(experiment)
            session.flush()
            for architecture in architectures:
                config = Configuration(architecture=architecture)
                session.add(config)
                session.flush()
                session.add(
                    Simulation(
                        configuration_id=config.id,
                        architecture=architecture,
                        benchmark=request.benchmark,
                        size=request.size,
                        experiment_id=experiment.id,
                    )
                )
            session.commit()
            return {**serialize(experiment), "total": len(architectures)}

    @app.get("/api/experiments")
    def experiments():
        with app.state.sessions() as session:
            return [
                serialize(e)
                for e in session.scalars(
                    select(Experiment).order_by(Experiment.created_at.desc()).limit(100)
                )
            ]

    @app.get("/api/experiments/{id}/results")
    def results(id: str):
        with app.state.sessions() as session:
            experiment = fetch(session, Experiment, id)
            runs = list(
                session.scalars(
                    select(Simulation)
                    .where(Simulation.experiment_id == id)
                    .order_by(Simulation.created_at, Simulation.id)
                )
            )
            counts = Counter(r.status for r in runs)
            terminal = sum(counts[s] for s in ("completed", "failed", "cancelled"))
            return {
                **serialize(experiment),
                "runs": [serialize(r) for r in runs],
                "counts": dict(counts),
                "total": len(runs),
                "finished": terminal,
            }

    @app.post("/api/experiments/compare")
    def comparison(request: CompareRequest):
        if len(set(request.simulation_ids)) != len(request.simulation_ids):
            raise HTTPException(422, "Select distinct simulations")
        with app.state.sessions() as session:
            runs = [fetch(session, Simulation, id) for id in request.simulation_ids]
            try:
                return compare(runs, request.max_cache_kib)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

    return app


app = create_app()
