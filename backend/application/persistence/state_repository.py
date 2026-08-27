from sqlalchemy import Engine, desc, select
from sqlalchemy.dialects.sqlite import insert

from application.persistence.schema import greenhouse_state_snapshots
from domain.state import GreenhouseState


class StateRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, state: GreenhouseState) -> None:
        row = {
            "greenhouse_id": state.greenhouse_id,
            "simulated_day": state.simulated_day,
            "timestamp": state.timestamp.isoformat(),
            "state_json": state.model_dump_json(),
        }
        statement = insert(greenhouse_state_snapshots).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["greenhouse_id", "simulated_day"],
            set_={"timestamp": row["timestamp"], "state_json": row["state_json"]},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get(self, greenhouse_id: str, *, day: int) -> GreenhouseState | None:
        statement = select(greenhouse_state_snapshots.c.state_json).where(
            greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id,
            greenhouse_state_snapshots.c.simulated_day == day,
        )
        with self._engine.connect() as connection:
            state_json = connection.execute(statement).scalar_one_or_none()
        return None if state_json is None else GreenhouseState.model_validate_json(state_json)

    def get_latest(self, greenhouse_id: str) -> GreenhouseState | None:
        statement = (
            select(greenhouse_state_snapshots.c.state_json)
            .where(greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id)
            .order_by(desc(greenhouse_state_snapshots.c.simulated_day))
            .limit(1)
        )
        with self._engine.connect() as connection:
            state_json = connection.execute(statement).scalar_one_or_none()
        return None if state_json is None else GreenhouseState.model_validate_json(state_json)

    def list_up_to_day(self, greenhouse_id: str, *, max_day: int) -> list[GreenhouseState]:
        statement = (
            select(greenhouse_state_snapshots.c.state_json)
            .where(
                greenhouse_state_snapshots.c.greenhouse_id == greenhouse_id,
                greenhouse_state_snapshots.c.simulated_day <= max_day,
            )
            .order_by(greenhouse_state_snapshots.c.simulated_day)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).scalars().all()
        return [GreenhouseState.model_validate_json(state_json) for state_json in rows]
