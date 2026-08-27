from datetime import UTC, datetime

from domain.enums import EventSource, EventType, ObservationType, PlantHealth, SourceType
from domain.event import Event
from domain.observation import Observation
from intelligence.state_reconstruction import (
    reconstruct_greenhouse_state,
    reconstruct_plant_state,
)

TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _obs(plant_id: str, observation_type: ObservationType, value: float) -> Observation:
    return Observation(
        observation_id=f"obs_{plant_id}_{observation_type.value}",
        greenhouse_id="gh_001",
        plant_id=plant_id,
        simulated_day=8,
        timestamp=TIMESTAMP,
        observation_type=observation_type,
        value=value,
        source_type=SourceType.SIMULATION,
    )


def _watering_event(plant_id: str) -> Event:
    return Event(
        event_id=f"evt_{plant_id}_watering",
        greenhouse_id="gh_001",
        plant_id=plant_id,
        simulated_day=8,
        timestamp=TIMESTAMP,
        event_type=EventType.WATERING,
        source=EventSource.SIMULATION,
    )


def test_reconstruct_plant_state_restates_latest_observation_values() -> None:
    observations = [
        _obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 55.0),
        _obs("plant_017", ObservationType.VISIBLE_FRUIT_COUNT, 47.0),
        _obs("plant_017", ObservationType.RIPE_FRUIT_COUNT, 12.0),
    ]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        day=8,
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_soil_moisture_pct == 55.0
    assert state.latest_visible_fruit_count == 47
    assert state.latest_ripe_fruit_count == 12
    assert state.health == PlantHealth.HEALTHY


def test_reconstruct_plant_state_flags_low_soil_moisture_as_action_required() -> None:
    observations = [_obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 15.0)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        day=8,
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.health == PlantHealth.ACTION_REQUIRED


def test_reconstruct_plant_state_flags_moderately_low_soil_moisture_as_monitor() -> None:
    observations = [_obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 32.0)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        day=8,
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.health == PlantHealth.MONITOR


def test_reconstruct_plant_state_ignores_other_plants_observations() -> None:
    observations = [_obs("plant_099", ObservationType.SOIL_MOISTURE_PCT, 55.0)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        day=8,
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_soil_moisture_pct is None
    assert state.health == PlantHealth.UNKNOWN


def test_reconstruct_plant_state_records_the_most_recent_event() -> None:
    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        day=8,
        timestamp=TIMESTAMP,
        observations=[],
        events=[_watering_event("plant_017")],
    )

    assert state.last_event_type == EventType.WATERING
    assert state.last_event_timestamp == TIMESTAMP


def test_reconstruct_greenhouse_state_aggregates_plant_states() -> None:
    plant_states = [
        reconstruct_plant_state(
            plant_id="plant_001",
            greenhouse_id="gh_001",
            day=8,
            timestamp=TIMESTAMP,
            observations=[_obs("plant_001", ObservationType.SOIL_MOISTURE_PCT, 55.0)],
            events=[],
        ),
        reconstruct_plant_state(
            plant_id="plant_002",
            greenhouse_id="gh_001",
            day=8,
            timestamp=TIMESTAMP,
            observations=[_obs("plant_002", ObservationType.SOIL_MOISTURE_PCT, 15.0)],
            events=[],
        ),
    ]

    state = reconstruct_greenhouse_state(
        greenhouse_id="gh_001", day=8, timestamp=TIMESTAMP, plant_states=plant_states
    )

    assert state.plants_healthy == 1
    assert state.plants_action_required == 1
