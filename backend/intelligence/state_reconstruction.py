from datetime import datetime

from domain.enums import ObservationType, PlantHealth
from domain.event import Event
from domain.observation import Observation
from domain.state import EnvironmentState, GreenhouseState, PlantState


def reconstruct_environment_state(
    plant_id: str, observations: list[Observation]
) -> EnvironmentState:
    plant_observations = [obs for obs in observations if obs.plant_id == plant_id]
    return EnvironmentState(
        soil_moisture_pct=_latest_value(plant_observations, ObservationType.SOIL_MOISTURE_PCT)
    )


_PLANT_OBSERVED_TYPES = frozenset(
    {
        ObservationType.VISIBLE_FRUIT_COUNT,
        ObservationType.RIPE_FRUIT_COUNT,
        ObservationType.ESTIMATED_RIPE_MASS_G,
        ObservationType.VISIBLE_HEIGHT_CM,
    }
)


def assess_plant_condition(plant_id: str, observations: list[Observation]) -> PlantHealth:
    """The plant's own condition - see PlantHealth's docstring for what
    that means and why this intentionally never reads soil moisture or any
    other environment reading (a plant can need watering while still being
    HEALTHY).

    UNKNOWN when nothing has been observed for the plant at all. MONITOR
    when a soil-moisture reading came in but none of the plant's own
    visible/fruit readings did (docs/archive/design-history/domain_model_eval_refactor_plan.md
    PR 3) - a real, if simple, anomaly-across-observations signal: e.g. the
    vision pipeline is down while the soil sensor still reports, so the
    plant's own state cannot be confirmed today. HEALTHY otherwise.
    """
    plant_observations = [obs for obs in observations if obs.plant_id == plant_id]
    if not plant_observations:
        return PlantHealth.UNKNOWN
    observed_types = {obs.observation_type for obs in plant_observations}
    if observed_types.isdisjoint(_PLANT_OBSERVED_TYPES):
        return PlantHealth.MONITOR
    return PlantHealth.HEALTHY


def reconstruct_plant_state(
    *,
    plant_id: str,
    greenhouse_id: str,
    timestamp: datetime,
    observations: list[Observation],
    events: list[Event],
) -> PlantState:
    plant_observations = [obs for obs in observations if obs.plant_id == plant_id]
    plant_events = [event for event in events if event.plant_id == plant_id]

    environment = reconstruct_environment_state(plant_id, observations)
    condition = assess_plant_condition(plant_id, observations)
    visible_fruit_count = _latest_value(plant_observations, ObservationType.VISIBLE_FRUIT_COUNT)
    ripe_fruit_count = _latest_value(plant_observations, ObservationType.RIPE_FRUIT_COUNT)
    ripe_mass_g = _latest_value(plant_observations, ObservationType.ESTIMATED_RIPE_MASS_G)
    visible_height_cm = _latest_value(plant_observations, ObservationType.VISIBLE_HEIGHT_CM)
    last_event = max(plant_events, key=lambda event: event.timestamp, default=None)

    return PlantState(
        plant_id=plant_id,
        greenhouse_id=greenhouse_id,
        timestamp=timestamp,
        health=condition,
        latest_soil_moisture_pct=environment.soil_moisture_pct,
        latest_visible_fruit_count=int(visible_fruit_count)
        if visible_fruit_count is not None
        else None,
        latest_ripe_fruit_count=int(ripe_fruit_count) if ripe_fruit_count is not None else None,
        latest_estimated_ripe_mass_g=ripe_mass_g,
        latest_visible_height_cm=visible_height_cm,
        last_event_type=last_event.event_type if last_event else None,
        last_event_timestamp=last_event.timestamp if last_event else None,
    )


def reconstruct_greenhouse_state(
    *,
    greenhouse_id: str,
    timestamp: datetime,
    plant_states: list[PlantState],
) -> GreenhouseState:
    return GreenhouseState.aggregate(
        greenhouse_id=greenhouse_id,
        timestamp=timestamp,
        plant_states=plant_states,
    )


def _latest_value(
    observations: list[Observation], observation_type: ObservationType
) -> float | None:
    matching = [obs for obs in observations if obs.observation_type == observation_type]
    latest = max(matching, key=lambda obs: obs.timestamp, default=None)
    return latest.value if latest is not None else None
