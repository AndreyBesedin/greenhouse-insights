from datetime import datetime

from sqlalchemy import Engine, delete, desc, select
from sqlalchemy.dialects.sqlite import insert

from application.persistence.schema import greenhouse_state_snapshots
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from domain.state import GreenhouseState


class StateRepository:
    """Reconstructed GreenhouseState snapshots, keyed by (greenhouse,
    timestamp). Every read is bounded by a timestamp so a caller looking
    at the greenhouse "as of" T can never see a snapshot from after T."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, state: GreenhouseState) -> None:
        row = {
            "greenhouse_id": state.greenhouse_id,
            "timestamp": to_db_timestamp(state.timestamp),
            "state_json": state.model_dump_json(),
        }
        statement = insert(greenhouse_state_snapshots).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["greenhouse_id", "timestamp"],
            set_={"state_json": row["state_json"]},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get_at(self, greenhouse_id: str, *, at: datetime) -> GreenhouseState | None:
        """The most recent snapshot taken at or before `at`."""
        statement = (
            select(greenhouse_state_snapshots.c.state_json)
            .where(
                greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id,
                greenhouse_state_snapshots.c.timestamp <= to_db_timestamp(at),
            )
            .order_by(desc(greenhouse_state_snapshots.c.timestamp))
            .limit(1)
        )
        with self._engine.connect() as connection:
            state_json = connection.execute(statement).scalar_one_or_none()
        return None if state_json is None else GreenhouseState.model_validate_json(state_json)

    def get_latest(self, greenhouse_id: str) -> GreenhouseState | None:
        statement = (
            select(greenhouse_state_snapshots.c.state_json)
            .where(greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id)
            .order_by(desc(greenhouse_state_snapshots.c.timestamp))
            .limit(1)
        )
        with self._engine.connect() as connection:
            state_json = connection.execute(statement).scalar_one_or_none()
        return None if state_json is None else GreenhouseState.model_validate_json(state_json)

    def list_up_to(self, greenhouse_id: str, *, up_to: datetime) -> list[GreenhouseState]:
        statement = (
            select(greenhouse_state_snapshots.c.state_json)
            .where(
                greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id,
                greenhouse_state_snapshots.c.timestamp <= to_db_timestamp(up_to),
            )
            .order_by(greenhouse_state_snapshots.c.timestamp)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).scalars().all()
        return [GreenhouseState.model_validate_json(state_json) for state_json in rows]

    def list_timestamps(self, greenhouse_id: str) -> list[datetime]:
        """Every snapshot instant, ascending - the greenhouse's navigable
        timeline, without loading the snapshots themselves."""
        statement = (
            select(greenhouse_state_snapshots.c.timestamp)
            .where(greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id)
            .order_by(greenhouse_state_snapshots.c.timestamp)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).scalars().all()
        return [from_db_timestamp(value) for value in rows]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(greenhouse_state_snapshots).where(
            greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id
        )
        with self._engine.begin() as connection:
            connection.execute(statement)
