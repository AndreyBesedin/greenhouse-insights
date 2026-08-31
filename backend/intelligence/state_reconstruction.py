from datetime import datetime

from domain.enums import ObservationType, PlantHealth
from domain.event import Event
from domain.observation import Observation
from domain.state import GreenhouseState, PlantState

_ACTION_REQUIRED_SOIL_MOISTURE_PCT = 20.0
_MONITOR_SOIL_MOISTURE_PCT = 40.0


def reconstruct_plant_state(
    *,
    plant_id: str,
    greenhouse_id: str,
    day: int,
    timestamp: datetime,
    observations: list[Observation],
    events: list[Event],
) -> PlantState:
    plant_observations = [obs for obs in observations if obs.plant_id == plant_id]
    plant_events = [event for event in events if event.plant_id == plant_id]

    soil_moisture = _latest_value(plant_observations, ObservationType.SOIL_MOISTURE_PCT)
    visible_fruit_count = _latest_value(plant_observations, ObservationType.VISIBLE_FRUIT_COUNT)
    ripe_fruit_count = _latest_value(plant_observations, ObservationType.RIPE_FRUIT_COUNT)
    ripe_mass_g = _latest_value(plant_observations, ObservationType.ESTIMATED_RIPE_MASS_G)
    last_event = max(plant_events, key=lambda event: event.timestamp, default=None)

    return PlantState(
        plant_id=plant_id,
        greenhouse_id=greenhouse_id,
        simulated_day=day,
        timestamp=timestamp,
        health=_health_from_soil_moisture(soil_moisture),
        latest_soil_moisture_pct=soil_moisture,
        latest_visible_fruit_count=int(visible_fruit_count)
        if visible_fruit_count is not None
        else None,
        latest_ripe_fruit_count=int(ripe_fruit_count) if ripe_fruit_count is not None else None,
        latest_estimated_ripe_mass_g=ripe_mass_g,
        last_event_type=last_event.event_type if last_event else None,
        last_event_timestamp=last_event.timestamp if last_event else None,
    )


def reconstruct_greenhouse_state(
    *,
    greenhouse_id: str,
    day: int,
    timestamp: datetime,
    plant_states: list[PlantState],
) -> GreenhouseState:
    return GreenhouseState.aggregate(
        greenhouse_id=greenhouse_id,
        simulated_day=day,
        timestamp=timestamp,
        plant_states=plant_states,
    )


def _latest_value(
    observations: list[Observation], observation_type: ObservationType
) -> float | None:
    matching = [obs for obs in observations if obs.observation_type == observation_type]
    latest = max(matching, key=lambda obs: obs.timestamp, default=None)
    return latest.value if latest is not None else None


def _health_from_soil_moisture(soil_moisture_pct: float | None) -> PlantHealth:
    if soil_moisture_pct is None:
        return PlantHealth.UNKNOWN
    if soil_moisture_pct < _ACTION_REQUIRED_SOIL_MOISTURE_PCT:
        return PlantHealth.ACTION_REQUIRED
    if soil_moisture_pct < _MONITOR_SOIL_MOISTURE_PCT:
        return PlantHealth.MONITOR
    return PlantHealth.HEALTHY
