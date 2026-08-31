from dataclasses import dataclass
from datetime import datetime

import numpy as np

from domain.enums import FruitStatus, ObservationType, SourceType
from domain.observation import Observation
from domain.world import GreenhouseWorld, PlantWorld
from simulation.rng import seeded_rng
from simulation.scenarios.config import ScenarioConfig


@dataclass(frozen=True)
class ObservationGeneration:
    observations: list[Observation]


def generate_observations(
    world: GreenhouseWorld, config: ScenarioConfig, *, day: int, timestamp: datetime
) -> ObservationGeneration:
    """Derives noisy observations from the (already-advanced) hidden world."""
    rng = seeded_rng(config.random_seed, day, "observations")

    observations: list[Observation] = [
        _air_temperature_observation(world, config, day, timestamp, rng)
    ]
    for plant in world.plants:
        observations.extend(_plant_observations(world, plant, config, day, timestamp, rng))

    return ObservationGeneration(observations=observations)


def _air_temperature_observation(
    world: GreenhouseWorld,
    config: ScenarioConfig,
    day: int,
    timestamp: datetime,
    rng: np.random.Generator,
) -> Observation:
    noisy = world.environment.air_temperature_c + rng.normal(0.0, config.air_temperature_noise_c)
    return Observation(
        observation_id=f"obs_{world.greenhouse_id}_d{day}_gh_air_temperature_c",
        greenhouse_id=world.greenhouse_id,
        plant_id=None,
        simulated_day=day,
        timestamp=timestamp,
        observation_type=ObservationType.AIR_TEMPERATURE_C,
        value=round(float(noisy), 1),
        source_type=SourceType.SIMULATION,
    )


def _plant_observations(
    world: GreenhouseWorld,
    plant: PlantWorld,
    config: ScenarioConfig,
    day: int,
    timestamp: datetime,
    rng: np.random.Generator,
) -> list[Observation]:
    def observation(observation_type: ObservationType, value: float) -> Observation:
        return Observation(
            observation_id=f"obs_{world.greenhouse_id}_d{day}_{plant.plant_id}_{observation_type.value}",
            greenhouse_id=world.greenhouse_id,
            plant_id=plant.plant_id,
            simulated_day=day,
            timestamp=timestamp,
            observation_type=observation_type,
            value=value,
            source_type=SourceType.SIMULATION,
        )

    soil_moisture_pct = 100.0 * plant.water_reservoir_ml / config.water_capacity_ml
    noisy_moisture = soil_moisture_pct + rng.normal(0.0, config.soil_moisture_noise_pct)
    noisy_moisture = float(np.clip(noisy_moisture, 0.0, 100.0))

    fruits = [fruit for truss in plant.trusses for fruit in truss.fruits]
    visible_fruits = [fruit for fruit in fruits if fruit.status != FruitStatus.HARVESTED]
    ripe_fruits = [fruit for fruit in visible_fruits if fruit.status == FruitStatus.RIPE]
    ripe_mass_g = sum(fruit.mass_g for fruit in ripe_fruits)
    noisy_ripe_mass = max(
        0.0, ripe_mass_g * (1 + rng.normal(0.0, config.ripe_mass_noise_pct / 100.0))
    )

    return [
        observation(ObservationType.SOIL_MOISTURE_PCT, round(noisy_moisture, 1)),
        observation(
            ObservationType.VISIBLE_FRUIT_COUNT,
            _noisy_count(len(visible_fruits), config.fruit_count_noise_probability, rng),
        ),
        observation(
            ObservationType.RIPE_FRUIT_COUNT,
            _noisy_count(len(ripe_fruits), config.fruit_count_noise_probability, rng),
        ),
        observation(ObservationType.ESTIMATED_RIPE_MASS_G, round(noisy_ripe_mass, 1)),
    ]


def _noisy_count(true_count: int, error_probability: float, rng: np.random.Generator) -> float:
    if rng.uniform(0.0, 1.0) < error_probability:
        delta = int(rng.choice([-1, 1]))
        true_count = max(0, true_count + delta)
    return float(true_count)
