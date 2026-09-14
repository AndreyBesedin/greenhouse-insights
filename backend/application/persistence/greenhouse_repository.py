from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import RowMapping

from application.persistence.schema import greenhouses
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant

_PLANTS_ADAPTER = TypeAdapter(list[Plant])


class GreenhouseRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, greenhouse: Greenhouse) -> None:
        row = {
            "greenhouse_id": greenhouse.greenhouse_id,
            "name": greenhouse.name,
            "description": greenhouse.description,
            "source_type": greenhouse.source_type.value,
            "crop": greenhouse.crop,
            "layout_json": greenhouse.layout.model_dump_json(),
            "plants_json": _plants_to_json(greenhouse.plants),
            "created_at": greenhouse.created_at.isoformat(),
            "current_state_timestamp": _optional_isoformat(greenhouse.current_state_timestamp),
            "latest_available_timestamp": _optional_isoformat(
                greenhouse.latest_available_timestamp
            ),
        }
        statement = insert(greenhouses).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["greenhouse_id"],
            set_={key: value for key, value in row.items() if key != "greenhouse_id"},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get(self, greenhouse_id: str) -> Greenhouse | None:
        statement = select(greenhouses).where(greenhouses.c.greenhouse_id == greenhouse_id)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_greenhouse(row)

    def list(self) -> list[Greenhouse]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(greenhouses)).mappings().all()
        return [_row_to_greenhouse(row) for row in rows]

    def delete(self, greenhouse_id: str) -> None:
        statement = delete(greenhouses).where(greenhouses.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _plants_to_json(plants: list[Plant]) -> str:
    return _PLANTS_ADAPTER.dump_json(plants).decode()


def _optional_isoformat(value: Any) -> str | None:
    return None if value is None else value.isoformat()


def _row_to_greenhouse(mapping: RowMapping) -> Greenhouse:
    return Greenhouse(
        greenhouse_id=mapping["greenhouse_id"],
        name=mapping["name"],
        description=mapping["description"],
        source_type=mapping["source_type"],
        crop=mapping["crop"],
        layout=GreenhouseLayout.model_validate_json(mapping["layout_json"]),
        plants=_PLANTS_ADAPTER.validate_json(mapping["plants_json"]),
        created_at=mapping["created_at"],
        current_state_timestamp=mapping["current_state_timestamp"],
        latest_available_timestamp=mapping["latest_available_timestamp"],
    )
