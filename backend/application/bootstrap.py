from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.simulation_repository import SimulationRepository
from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from simulation.definitions import SimulationDefinition
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.scenarios.config import ScenarioConfig


def bootstrap_greenhouses(engine: Engine) -> None:
    greenhouse_repo = GreenhouseRepository(engine)
    simulation_repo = SimulationRepository(engine)

    for config in SCENARIO_REGISTRY.values():
        if greenhouse_repo.get(config.greenhouse_id) is not None:
            continue

        greenhouse_repo.save(_greenhouse_from_config(config))
        simulation_repo.save(_simulation_definition_from_config(config))


def _greenhouse_from_config(config: ScenarioConfig) -> Greenhouse:
    return Greenhouse(
        greenhouse_id=config.greenhouse_id,
        name=config.name,
        description=config.description,
        source_type=SourceType.SIMULATION,
        layout=GreenhouseLayout(rows=config.rows, columns=config.columns),
        plants=_plants_from_config(config),
        created_at=datetime.now(UTC),
    )


def _plants_from_config(config: ScenarioConfig) -> list[Plant]:
    plants = []
    index = 0
    for row in range(1, config.rows + 1):
        for position_in_row in range(1, config.columns + 1):
            index += 1
            plants.append(
                Plant(
                    plant_id=f"{config.greenhouse_id}_plant_{index:03d}",
                    variety=config.variety,
                    row=row,
                    position_in_row=position_in_row,
                )
            )
    return plants


def _simulation_definition_from_config(config: ScenarioConfig) -> SimulationDefinition:
    return SimulationDefinition(
        simulation_id=f"sim_{config.greenhouse_id}",
        greenhouse_id=config.greenhouse_id,
        scenario_definition=config.greenhouse_id,
        start_date=config.start_date,
        duration_days=config.duration_days,
        random_seed=config.random_seed,
        total_steps=config.duration_days,
    )
