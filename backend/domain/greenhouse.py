from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from domain.enums import SourceType


class Plant(BaseModel):
    plant_id: str
    variety: str
    row: int
    position_in_row: int
    x: float | None = None
    y: float | None = None
    zone: str | None = None
    tray_id: str | None = None


class GreenhouseLayout(BaseModel):
    kind: Literal["grid"] = "grid"
    rows: int
    columns: int


class Greenhouse(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    source_type: SourceType
    layout: GreenhouseLayout
    plants: list[Plant]
    created_at: datetime
    current_state_timestamp: datetime | None = None
    latest_available_timestamp: datetime | None = None


def build_grid_plants(greenhouse_id: str, variety: str, rows: int, columns: int) -> list[Plant]:
    plants = []
    index = 0
    for row in range(1, rows + 1):
        for position_in_row in range(1, columns + 1):
            index += 1
            plants.append(
                Plant(
                    plant_id=f"{greenhouse_id}_plant_{index:03d}",
                    variety=variety,
                    row=row,
                    position_in_row=position_in_row,
                )
            )
    return plants
