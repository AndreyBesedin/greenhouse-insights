from datetime import datetime

from pydantic import BaseModel

from domain.enums import EventType, PlantHealth, Provenance


class EnvironmentState(BaseModel):
    """The reconstructed environment around a plant: soil moisture today,
    with room for future readings (air temperature, humidity, ...). This is
    not plant health - see PlantHealth."""

    soil_moisture_pct: float | None = None


class PlantState(BaseModel):
    plant_id: str
    greenhouse_id: str
    timestamp: datetime
    health: PlantHealth
    latest_soil_moisture_pct: float | None = None
    latest_visible_fruit_count: int | None = None
    latest_ripe_fruit_count: int | None = None
    latest_estimated_ripe_mass_g: float | None = None
    latest_visible_height_cm: float | None = None
    harvested_total_g: float = 0.0
    last_event_type: EventType | None = None
    last_event_timestamp: datetime | None = None
    provenance: Provenance = Provenance.DETERMINISTICALLY_DERIVED


class GreenhouseState(BaseModel):
    """A reconstructed snapshot of the whole greenhouse at one instant.

    Chronology is the timestamp alone: a simulation-run's day counter is a
    simulation mechanic (simulation/, GreenhouseWorld) and never leaks into
    generic domain records, so the same snapshot shape serves simulated,
    recorded and live greenhouses
    (docs/design/wur_real_data_ingestion_replay_plan.md section 9)."""

    greenhouse_id: str
    timestamp: datetime
    plant_states: list[PlantState]
    plants_healthy: int
    plants_monitor: int
    plants_action_required: int
    total_ripe_mass_g: float = 0.0
    total_harvested_g: float = 0.0

    @classmethod
    def aggregate(
        cls,
        *,
        greenhouse_id: str,
        timestamp: datetime,
        plant_states: list[PlantState],
    ) -> "GreenhouseState":
        return cls(
            greenhouse_id=greenhouse_id,
            timestamp=timestamp,
            plant_states=plant_states,
            plants_healthy=sum(1 for s in plant_states if s.health == PlantHealth.HEALTHY),
            plants_monitor=sum(1 for s in plant_states if s.health == PlantHealth.MONITOR),
            plants_action_required=sum(
                1 for s in plant_states if s.health == PlantHealth.ACTION_REQUIRED
            ),
            total_ripe_mass_g=sum(s.latest_estimated_ripe_mass_g or 0.0 for s in plant_states),
            total_harvested_g=sum(s.harvested_total_g for s in plant_states),
        )
