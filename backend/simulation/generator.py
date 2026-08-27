from dataclasses import dataclass
from datetime import datetime

import numpy as np

from domain.enums import EventSource, EventType, ObservationType, SourceType
from domain.event import Event
from domain.observation import Observation
from simulation.scenarios.config import ScenarioConfig


@dataclass(frozen=True)
class DayGeneration:
    observations: list[Observation]
    events: list[Event]


def generate_day(
    config: ScenarioConfig,
    greenhouse_id: str,
    plant_ids: list[str],
    *,
    day: int,
    timestamp: datetime,
) -> DayGeneration:
    rng = np.random.default_rng(np.random.SeedSequence([config.random_seed, day]))

    observations: list[Observation] = [
        _greenhouse_temperature_observation(config, greenhouse_id, day, timestamp, rng)
    ]
    events: list[Event] = []

    for plant_id in plant_ids:
        observations.extend(
            _plant_observations(config, greenhouse_id, plant_id, day, timestamp, rng)
        )
        if day % config.watering_interval_days == 0:
            events.append(_watering_event(greenhouse_id, plant_id, day, timestamp))

    return DayGeneration(observations=observations, events=events)


def _greenhouse_temperature_observation(
    config: ScenarioConfig,
    greenhouse_id: str,
    day: int,
    timestamp: datetime,
    rng: np.random.Generator,
) -> Observation:
    low, high = config.air_temperature_bounds
    return Observation(
        observation_id=f"obs_{greenhouse_id}_d{day}_gh_air_temperature_c",
        greenhouse_id=greenhouse_id,
        plant_id=None,
        simulated_day=day,
        timestamp=timestamp,
        observation_type=ObservationType.AIR_TEMPERATURE_C,
        value=round(float(rng.uniform(low, high)), 1),
        source_type=SourceType.SIMULATION,
    )


def _plant_observations(
    config: ScenarioConfig,
    greenhouse_id: str,
    plant_id: str,
    day: int,
    timestamp: datetime,
    rng: np.random.Generator,
) -> list[Observation]:
    moisture_low, moisture_high = config.soil_moisture_bounds
    fruit_low, fruit_high = config.fruit_count_bounds

    visible_fruit_count = int(rng.integers(fruit_low, fruit_high + 1))
    ripe_fruit_count = int(rng.integers(0, visible_fruit_count + 1))

    def observation(observation_type: ObservationType, value: float) -> Observation:
        return Observation(
            observation_id=f"obs_{greenhouse_id}_d{day}_{plant_id}_{observation_type.value}",
            greenhouse_id=greenhouse_id,
            plant_id=plant_id,
            simulated_day=day,
            timestamp=timestamp,
            observation_type=observation_type,
            value=value,
            source_type=SourceType.SIMULATION,
        )

    return [
        observation(
            ObservationType.SOIL_MOISTURE_PCT,
            round(float(rng.uniform(moisture_low, moisture_high)), 1),
        ),
        observation(ObservationType.VISIBLE_FRUIT_COUNT, float(visible_fruit_count)),
        observation(ObservationType.RIPE_FRUIT_COUNT, float(ripe_fruit_count)),
    ]


def _watering_event(greenhouse_id: str, plant_id: str, day: int, timestamp: datetime) -> Event:
    return Event(
        event_id=f"evt_{greenhouse_id}_d{day}_{plant_id}_watering",
        greenhouse_id=greenhouse_id,
        plant_id=plant_id,
        simulated_day=day,
        timestamp=timestamp,
        event_type=EventType.WATERING,
        source=EventSource.SIMULATION,
    )
