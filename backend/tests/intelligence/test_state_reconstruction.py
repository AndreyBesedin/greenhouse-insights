from datetime import UTC, datetime, timedelta

from domain.enums import EventSource, EventType, ObservationType, PlantHealth, SourceType
from domain.event import Event
from domain.observation import Observation
from domain.provenance import RecordSource
from intelligence.state_reconstruction import (
    reconstruct_greenhouse_environment,
    reconstruct_greenhouse_state,
    reconstruct_plant_state,
)

TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _obs(plant_id: str, observation_type: ObservationType, value: float) -> Observation:
    return Observation(
        observation_id=f"obs_{plant_id}_{observation_type.value}",
        greenhouse_id="gh_001",
        plant_id=plant_id,
        timestamp=TIMESTAMP,
        observation_type=observation_type,
        value=value,
        source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_001"),
    )


def _watering_event(plant_id: str) -> Event:
    return Event(
        event_id=f"evt_{plant_id}_watering",
        greenhouse_id="gh_001",
        plant_id=plant_id,
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
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_soil_moisture_pct == 55.0
    assert state.latest_visible_fruit_count == 47
    assert state.latest_ripe_fruit_count == 12
    assert state.health == PlantHealth.HEALTHY


def test_reconstruct_plant_state_restates_latest_visible_height() -> None:
    observations = [_obs("plant_017", ObservationType.VISIBLE_HEIGHT_CM, 132.5)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_visible_height_cm == 132.5


def test_reconstruct_plant_state_stays_healthy_despite_critically_low_soil_moisture() -> None:
    """The environment/health distinction (PR 2): low soil moisture is
    environment data that may trigger watering, but it does not by itself
    make the plant's own condition unhealthy - as long as the plant's own
    readings (fruit/height) were otherwise captured today."""
    observations = [
        _obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 5.0),
        _obs("plant_017", ObservationType.VISIBLE_FRUIT_COUNT, 3.0),
    ]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_soil_moisture_pct == 5.0
    assert state.health == PlantHealth.HEALTHY


def test_reconstruct_plant_state_stays_healthy_across_the_full_moisture_range() -> None:
    for moisture_pct in (2.0, 15.0, 32.0, 55.0, 95.0):
        observations = [
            _obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, moisture_pct),
            _obs("plant_017", ObservationType.VISIBLE_FRUIT_COUNT, 3.0),
        ]

        state = reconstruct_plant_state(
            plant_id="plant_017",
            greenhouse_id="gh_001",
            timestamp=TIMESTAMP,
            observations=observations,
            events=[],
        )

        assert state.health == PlantHealth.HEALTHY


def test_reconstruct_plant_state_flags_monitor_when_only_environment_data_arrives() -> None:
    """A soil-moisture reading with none of the plant's own visible/fruit
    readings (e.g. the vision pipeline is down) is a genuine condition
    concern, independent of what the moisture value itself is (PR 3)."""
    observations = [_obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 75.0)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        observations=observations,
        events=[],
    )

    assert state.latest_soil_moisture_pct == 75.0
    assert state.health == PlantHealth.MONITOR


def test_reconstruct_plant_state_ignores_other_plants_observations() -> None:
    observations = [_obs("plant_099", ObservationType.SOIL_MOISTURE_PCT, 55.0)]

    state = reconstruct_plant_state(
        plant_id="plant_017",
        greenhouse_id="gh_001",
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
            timestamp=TIMESTAMP,
            observations=[
                _obs("plant_001", ObservationType.SOIL_MOISTURE_PCT, 55.0),
                _obs("plant_001", ObservationType.VISIBLE_FRUIT_COUNT, 4.0),
            ],
            events=[],
        ),
        reconstruct_plant_state(
            plant_id="plant_002",
            greenhouse_id="gh_001",
            timestamp=TIMESTAMP,
            observations=[_obs("plant_002", ObservationType.SOIL_MOISTURE_PCT, 15.0)],
            events=[],
        ),
        reconstruct_plant_state(
            plant_id="plant_003",
            greenhouse_id="gh_001",
            timestamp=TIMESTAMP,
            observations=[],
            events=[],
        ),
    ]

    state = reconstruct_greenhouse_state(
        greenhouse_id="gh_001", timestamp=TIMESTAMP, plant_states=plant_states
    )

    # plant_001 has its full daily reading set (HEALTHY), plant_002 only a
    # moisture reading despite low moisture not being the point here
    # (MONITOR - its own state is unconfirmed), plant_003 has no
    # observations yet (UNKNOWN, falls into no bucket).
    assert state.plants_healthy == 1
    assert state.plants_monitor == 1
    assert state.plants_action_required == 0


def _greenhouse_obs(
    observation_type: ObservationType, value: float, *, at: datetime = TIMESTAMP
) -> Observation:
    return Observation(
        observation_id=f"obs_gh_{observation_type.value}_{at.isoformat()}",
        greenhouse_id="gh_001",
        plant_id=None,
        timestamp=at,
        observation_type=observation_type,
        value=value,
        source=RecordSource(type=SourceType.IMPORTED_DATA, source_id="wur"),
    )


def test_greenhouse_environment_takes_the_latest_greenhouse_level_reading_per_type() -> None:
    earlier = TIMESTAMP - timedelta(hours=1)
    observations = [
        _greenhouse_obs(ObservationType.AIR_TEMPERATURE_C, 21.0, at=TIMESTAMP),
        _greenhouse_obs(ObservationType.AIR_TEMPERATURE_C, 19.0, at=earlier),
        _greenhouse_obs(ObservationType.CO2_PPM, 812.0),
        # plant-level readings never describe the greenhouse environment
        _obs("plant_017", ObservationType.SOIL_MOISTURE_PCT, 40.0),
    ]

    environment = reconstruct_greenhouse_environment(observations)

    assert environment.air_temperature_c == 21.0
    assert environment.co2_ppm == 812.0
    assert environment.relative_humidity_pct is None


def test_greenhouse_state_carries_environment_and_compartment_level_harvest() -> None:
    harvest = Event(
        event_id="evt_harvest",
        greenhouse_id="gh_001",
        plant_id=None,
        timestamp=TIMESTAMP,
        event_type=EventType.HARVEST,
        source=EventSource.HUMAN_REPORTED,
        parameters={"harvested_mass_g": 1250.0},
    )

    state = reconstruct_greenhouse_state(
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        plant_states=[],
        observations=[_greenhouse_obs(ObservationType.RELATIVE_HUMIDITY_PCT, 78.5)],
        events=[harvest],
    )

    assert state.environment.relative_humidity_pct == 78.5
    assert state.total_harvested_g == 1250.0
    assert state.plant_states == []
