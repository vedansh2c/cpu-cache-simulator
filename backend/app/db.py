import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, Float, Integer, String, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(UTC).isoformat()


def identifier():
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Configuration(Base):
    __tablename__ = "configurations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=identifier)
    created_at: Mapped[str] = mapped_column(String, default=now)
    architecture: Mapped[dict] = mapped_column(JSON)


class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=identifier)
    created_at: Mapped[str] = mapped_column(String, default=now, index=True)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    configuration_id: Mapped[str] = mapped_column(String)
    architecture: Mapped[dict] = mapped_column(JSON)
    benchmark: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[str | None] = mapped_column(String)
    finished_at: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(String)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    wall_seconds: Mapped[float | None] = mapped_column(Float)
    experiment_id: Mapped[str | None] = mapped_column(String, index=True)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=identifier)
    created_at: Mapped[str] = mapped_column(String, default=now)
    definition: Mapped[dict] = mapped_column(JSON)


def database(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{data_dir / 'platform.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def sqlite_settings(connection, _):
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(simulations)"))}
        if "experiment_id" not in columns:
            connection.execute(text("ALTER TABLE simulations ADD COLUMN experiment_id VARCHAR"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_simulations_experiment_id "
                "ON simulations (experiment_id)"
            )
        )
    return sessionmaker(engine, expire_on_commit=False)
