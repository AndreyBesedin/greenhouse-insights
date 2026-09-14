from datetime import datetime

from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.persistence.schema import observations
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from domain.observation import Observation
from domain.provenance import RecordSource


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
        up_to: datetime | None = None,
    ) -> list[Observation]:
        """Observations in chronological order, optionally only those
        observed at or before `up_to` - the temporal-honesty boundary every
        reader (state reconstruction, policies, replay) must respect."""
        statement = select(observations).where(observations.c.greenhouse_id == greenhouse_id)
        if plant_id is not None:
            statement = statement.where(observations.c.plant_id == plant_id)
        if up_to is not None:
            statement = statement.where(observations.c.timestamp <= to_db_timestamp(up_to))
        statement = statement.order_by(observations.c.timestamp)

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
        "timestamp": to_db_timestamp(observation.timestamp),
        "observation_type": observation.observation_type.value,
        "value": observation.value,
        "source_type": observation.source.type.value,
        "source_id": observation.source.source_id,
    }


def _row_to_observation(mapping: RowMapping) -> Observation:
    return Observation(
        observation_id=mapping["observation_id"],
        greenhouse_id=mapping["greenhouse_id"],
        plant_id=mapping["plant_id"],
        timestamp=from_db_timestamp(mapping["timestamp"]),
        observation_type=mapping["observation_type"],
        value=mapping["value"],
        source=RecordSource(type=mapping["source_type"], source_id=mapping["source_id"]),
    )
