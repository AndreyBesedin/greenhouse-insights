from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import EventSource, EventType


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    greenhouse_id: str
    plant_id: str | None
    timestamp: datetime
    event_type: EventType
    source: EventSource
    confidence: float = 1.0
    parameters: dict[str, Any] = Field(default_factory=dict)
