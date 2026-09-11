from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
    """ "grid": plants laid out in rows x columns (the simulator). "compartment":
    a physical compartment observed as a whole, with no individually
    identified plants (a recorded dataset's climate compartment) - rows and
    columns are then 0. Positions inside a compartment are a later spatial
    model (docs/design/wur_real_data_ingestion_replay_plan.md section 7)."""

    kind: Literal["grid", "compartment"] = "grid"
    rows: int = Field(ge=0)
    columns: int = Field(ge=0)


class Greenhouse(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    source_type: SourceType
    # The crop grown, independent of whether individual plants are known.
    crop: str | None = None
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
