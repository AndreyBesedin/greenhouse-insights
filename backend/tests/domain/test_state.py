from datetime import UTC, datetime

from domain.enums import EventType, PlantHealth, Provenance
from domain.state import GreenhouseState, PlantState

TIMESTAMP = datetime(2026, 1, 13, 0, 0, tzinfo=UTC)


def _make_plant_state(plant_id: str, health: PlantHealth) -> PlantState:
    return PlantState(
        plant_id=plant_id,
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        health=health,
    )


def test_plant_state_constructs_with_required_fields() -> None:
    state = _make_plant_state("plant_017", PlantHealth.HEALTHY)

    assert state.health == PlantHealth.HEALTHY
    assert state.latest_soil_moisture_pct is None
    assert state.last_event_type is None


def test_plant_state_provenance_defaults_to_deterministically_derived() -> None:
    state = _make_plant_state("plant_017", PlantHealth.HEALTHY)

    assert state.provenance == Provenance.DETERMINISTICALLY_DERIVED


def test_plant_state_accepts_latest_observation_values_and_last_event() -> None:
    state = PlantState(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        health=PlantHealth.MONITOR,
        latest_soil_moisture_pct=38.0,
        latest_visible_fruit_count=47,
        latest_ripe_fruit_count=12,
        last_event_type=EventType.WATERING,
        last_event_timestamp=TIMESTAMP,
    )

    assert state.latest_soil_moisture_pct == 38.0
    assert state.latest_visible_fruit_count == 47
    assert state.last_event_type == EventType.WATERING


def test_greenhouse_state_aggregate_counts_plant_health_buckets() -> None:
    plant_states = [
        _make_plant_state("plant_001", PlantHealth.HEALTHY),
        _make_plant_state("plant_002", PlantHealth.HEALTHY),
        _make_plant_state("plant_003", PlantHealth.MONITOR),
        _make_plant_state("plant_004", PlantHealth.ACTION_REQUIRED),
    ]

    state = GreenhouseState.aggregate(
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        plant_states=plant_states,
    )

    assert state.plants_healthy == 2
    assert state.plants_monitor == 1
    assert state.plants_action_required == 1
    assert state.plant_states == plant_states


def test_plant_health_has_expected_members() -> None:
    assert {member.value for member in PlantHealth} == {
        "HEALTHY",
        "MONITOR",
        "ACTION_REQUIRED",
        "UNKNOWN",
    }


def test_provenance_has_expected_members() -> None:
    assert {member.value for member in Provenance} == {
        "OBSERVED",
        "REPORTED",
        "DETERMINISTICALLY_DERIVED",
        "INFERRED",
    }
