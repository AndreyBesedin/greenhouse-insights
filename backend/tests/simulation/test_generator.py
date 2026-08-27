from datetime import UTC, datetime

from domain.enums import EventType, ObservationType
from simulation.generator import generate_day
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_IDS = ["gh_001_plant_001", "gh_001_plant_002"]
TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def test_generate_day_is_deterministic_for_the_same_inputs() -> None:
    first = generate_day(CONFIG, "gh_001", PLANT_IDS, day=8, timestamp=TIMESTAMP)
    second = generate_day(CONFIG, "gh_001", PLANT_IDS, day=8, timestamp=TIMESTAMP)

    assert first.observations == second.observations
    assert first.events == second.events


def test_generate_day_differs_across_days() -> None:
    day_8 = generate_day(CONFIG, "gh_001", PLANT_IDS, day=8, timestamp=TIMESTAMP)
    day_9 = generate_day(CONFIG, "gh_001", PLANT_IDS, day=9, timestamp=TIMESTAMP)

    assert day_8.observations != day_9.observations


def test_generate_day_emits_soil_moisture_within_configured_bounds() -> None:
    generation = generate_day(CONFIG, "gh_001", PLANT_IDS, day=1, timestamp=TIMESTAMP)

    low, high = CONFIG.soil_moisture_bounds
    moisture_readings = [
        obs.value
        for obs in generation.observations
        if obs.observation_type == ObservationType.SOIL_MOISTURE_PCT
    ]
    assert len(moisture_readings) == len(PLANT_IDS)
    assert all(low <= value <= high for value in moisture_readings)


def test_generate_day_emits_one_greenhouse_level_temperature_reading() -> None:
    generation = generate_day(CONFIG, "gh_001", PLANT_IDS, day=1, timestamp=TIMESTAMP)

    temperature_readings = [
        obs
        for obs in generation.observations
        if obs.observation_type == ObservationType.AIR_TEMPERATURE_C
    ]
    assert len(temperature_readings) == 1
    assert temperature_readings[0].plant_id is None
    low, high = CONFIG.air_temperature_bounds
    assert low <= temperature_readings[0].value <= high


def test_generate_day_emits_ripe_fruit_count_never_above_visible_fruit_count() -> None:
    generation = generate_day(CONFIG, "gh_001", PLANT_IDS, day=15, timestamp=TIMESTAMP)

    by_plant: dict[str, dict[ObservationType, float]] = {}
    for obs in generation.observations:
        if obs.plant_id is not None:
            by_plant.setdefault(obs.plant_id, {})[obs.observation_type] = obs.value

    for readings in by_plant.values():
        assert (
            readings[ObservationType.RIPE_FRUIT_COUNT]
            <= readings[ObservationType.VISIBLE_FRUIT_COUNT]
        )


def test_generate_day_emits_watering_event_on_the_configured_interval() -> None:
    watering_day = generate_day(
        CONFIG, "gh_001", PLANT_IDS, day=CONFIG.watering_interval_days, timestamp=TIMESTAMP
    )
    non_watering_day = generate_day(
        CONFIG, "gh_001", PLANT_IDS, day=CONFIG.watering_interval_days + 1, timestamp=TIMESTAMP
    )

    watering_events = [e for e in watering_day.events if e.event_type == EventType.WATERING]
    assert {e.plant_id for e in watering_events} == set(PLANT_IDS)
    assert not [e for e in non_watering_day.events if e.event_type == EventType.WATERING]
