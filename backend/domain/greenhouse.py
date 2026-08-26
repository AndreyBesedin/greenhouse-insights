from pydantic import BaseModel


class Plant(BaseModel):
    plant_id: str
    variety: str
    row: int
    position_in_row: int
    x: float | None = None
    y: float | None = None
    zone: str | None = None
    tray_id: str | None = None
