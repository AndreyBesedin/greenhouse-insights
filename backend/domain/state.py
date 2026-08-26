from datetime import datetime

from pydantic import BaseModel

from domain.enums import EventType, PlantHealth, Provenance


class PlantState(BaseModel):
    plant_id: str
    greenhouse_id: str
    simulated_day: int
    timestamp: datetime
    health: PlantHealth
    latest_soil_moisture_pct: float | None = None
    latest_visible_fruit_count: int | None = None
    latest_ripe_fruit_count: int | None = None
    last_event_type: EventType | None = None
    last_event_timestamp: datetime | None = None
    provenance: Provenance = Provenance.DETERMINISTICALLY_DERIVED


class GreenhouseState(BaseModel):
    greenhouse_id: str
    simulated_day: int
    timestamp: datetime
    plant_states: list[PlantState]
    plants_healthy: int
    plants_monitor: int
    plants_action_required: int

    @classmethod
    def aggregate(
        cls,
        *,
        greenhouse_id: str,
        simulated_day: int,
        timestamp: datetime,
        plant_states: list[PlantState],
    ) -> "GreenhouseState":
        return cls(
            greenhouse_id=greenhouse_id,
            simulated_day=simulated_day,
            timestamp=timestamp,
            plant_states=plant_states,
            plants_healthy=sum(1 for s in plant_states if s.health == PlantHealth.HEALTHY),
            plants_monitor=sum(1 for s in plant_states if s.health == PlantHealth.MONITOR),
            plants_action_required=sum(
                1 for s in plant_states if s.health == PlantHealth.ACTION_REQUIRED
            ),
        )
