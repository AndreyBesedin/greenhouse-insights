import json
from datetime import datetime

from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.persistence.schema import events
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from domain.event import Event


class EventRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_many(self, items: list[Event]) -> None:
        if not items:
            return
        rows = [_event_to_row(item) for item in items]
        with self._engine.begin() as connection:
            connection.execute(events.insert(), rows)

    def list_for_greenhouse(
        self,
        greenhouse_id: str,
        *,
        plant_id: str | None = None,
        up_to: datetime | None = None,
    ) -> list[Event]:
        statement = select(events).where(events.c.greenhouse_id == greenhouse_id)
        if plant_id is not None:
            statement = statement.where(events.c.plant_id == plant_id)
        if up_to is not None:
            statement = statement.where(events.c.timestamp <= to_db_timestamp(up_to))
        statement = statement.order_by(events.c.timestamp)

        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_event(row) for row in rows]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(events).where(events.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _event_to_row(event: Event) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "greenhouse_id": event.greenhouse_id,
        "plant_id": event.plant_id,
        "timestamp": to_db_timestamp(event.timestamp),
        "event_type": event.event_type.value,
        "source": event.source.value,
        "confidence": event.confidence,
        "parameters_json": json.dumps(event.parameters),
    }


def _row_to_event(mapping: RowMapping) -> Event:
    return Event(
        event_id=mapping["event_id"],
        greenhouse_id=mapping["greenhouse_id"],
        plant_id=mapping["plant_id"],
        timestamp=from_db_timestamp(mapping["timestamp"]),
        event_type=mapping["event_type"],
        source=mapping["source"],
        confidence=mapping["confidence"],
        parameters=json.loads(mapping["parameters_json"]),
    )
