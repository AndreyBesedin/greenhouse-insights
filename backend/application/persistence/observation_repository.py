from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.persistence.schema import observations
from domain.observation import Observation


class ObservationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_many(self, items: list[Observation]) -> None:
        if not items:
            return
        rows = [_observation_to_row(item) for item in items]
        with self._engine.begin() as connection:
            connection.execute(observations.insert(), rows)

    def list_for_greenhouse(
        self,
        greenhouse_id: str,
        *,
        plant_id: str | None = None,
        max_day: int | None = None,
    ) -> list[Observation]:
        statement = select(observations).where(observations.c.greenhouse_id == greenhouse_id)
        if plant_id is not None:
            statement = statement.where(observations.c.plant_id == plant_id)
        if max_day is not None:
            statement = statement.where(observations.c.simulated_day <= max_day)
        statement = statement.order_by(observations.c.simulated_day)

        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_observation(row) for row in rows]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(observations).where(observations.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _observation_to_row(observation: Observation) -> dict[str, object]:
    return {
        "observation_id": observation.observation_id,
        "greenhouse_id": observation.greenhouse_id,
        "plant_id": observation.plant_id,
        "simulated_day": observation.simulated_day,
        "timestamp": observation.timestamp.isoformat(),
        "observation_type": observation.observation_type.value,
        "value": observation.value,
        "source_type": observation.source_type.value,
    }


def _row_to_observation(mapping: RowMapping) -> Observation:
    return Observation(
        observation_id=mapping["observation_id"],
        greenhouse_id=mapping["greenhouse_id"],
        plant_id=mapping["plant_id"],
        simulated_day=mapping["simulated_day"],
        timestamp=mapping["timestamp"],
        observation_type=mapping["observation_type"],
        value=mapping["value"],
        source_type=mapping["source_type"],
    )
