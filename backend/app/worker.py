import fcntl
import json
import logging
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, text, update

from app.db import Simulation, database, now
from app.runner import Cancelled, run_simulation, simulator_version
from app.settings import Settings

logger = logging.getLogger(__name__)


def claim(sessions):
    with sessions() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        run = session.scalar(
            select(Simulation)
            .where(Simulation.status == "queued")
            .order_by(Simulation.created_at, Simulation.id)
            .limit(1)
        )
        if run:
            run.status = "running"
            run.started_at = now()
        session.commit()
        return run


def execute(settings, sessions, run, stop, version):
    def cancelled():
        with sessions() as session:
            return stop.is_set() or session.get(Simulation, run.id).status == "cancelled"

    values = {}
    try:
        metrics, elapsed = run_simulation(settings, run, cancelled, version)
        values = {"status": "completed", "metrics": metrics, "wall_seconds": elapsed}
    except Cancelled as error:
        values = {"status": "cancelled", "error": str(error)}
    except Exception as error:
        logger.exception("Simulation %s failed", run.id)
        values = {"status": "failed", "error": str(error)[:1000]}
    with sessions() as session:
        # A cancellation wins a race with process completion.
        session.execute(
            update(Simulation)
            .where(Simulation.id == run.id, Simulation.status == "running")
            .values(**values, finished_at=now())
        )
        session.commit()


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    # One scheduler owns this volume; concurrency is inside its process.
    with (settings.data_dir / "worker.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        version = simulator_version(settings.gem5)
        sessions = database(settings.data_dir)
        with sessions() as session:
            session.execute(
                update(Simulation)
                .where(Simulation.status == "running")
                .values(
                    status="failed", error="Worker restarted during simulation", finished_at=now()
                )
            )
            session.commit()
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stop.set())
        heartbeat = settings.data_dir / "worker.json"
        try:
            with ThreadPoolExecutor(max_workers=settings.concurrency) as pool:
                pending = set()
                while not stop.is_set():
                    temporary = heartbeat.with_suffix(".tmp")
                    temporary.write_text(
                        json.dumps({"timestamp": time.time(), "gem5_version": version})
                    )
                    temporary.replace(heartbeat)
                    for future in list(pending):
                        if future.done():
                            future.result()
                            pending.remove(future)
                    if len(pending) < settings.concurrency:
                        run = claim(sessions)
                        if run:
                            pending.add(
                                pool.submit(execute, settings, sessions, run, stop, version)
                            )
                            continue
                    stop.wait(0.25)
        finally:
            heartbeat.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
