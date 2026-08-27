from datetime import date

from pydantic import BaseModel


class ScenarioConfig(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    variety: str
    rows: int
    columns: int
    start_date: date
    duration_days: int
    random_seed: int
    soil_moisture_bounds: tuple[float, float] = (25.0, 70.0)
    air_temperature_bounds: tuple[float, float] = (18.0, 32.0)
    fruit_count_bounds: tuple[int, int] = (0, 60)
    watering_interval_days: int = 3
