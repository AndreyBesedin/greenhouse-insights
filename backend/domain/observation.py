from datetime import datetime

from pydantic import BaseModel, ConfigDict

from domain.enums import ObservationType
from domain.provenance import RecordSource


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    greenhouse_id: str
    plant_id: str | None
    simulated_day: int
    timestamp: datetime
    observation_type: ObservationType
    value: float
    source: RecordSource
