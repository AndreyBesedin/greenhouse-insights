from datetime import datetime

from domain.enums import EventSource, EventType, FruitStatus
from domain.event import Event
from domain.world import GreenhouseWorld, PlantWorld
from management.validation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    ScheduleInspectionAction,
    WaterPlantAction,
)
from simulation.dynamics.water import apply_irrigation
from simulation.scenarios.config import ScenarioConfig


def apply_action(
    world: GreenhouseWorld,
    action: RequestedAction,
    config: ScenarioConfig,
    *,
    day: int,
    timestamp: datetime,
) -> tuple[GreenhouseWorld, Event]:
    """Applies an already-validated action, returning the updated world and its Event.

    This is the simulation's actioner (docs/design/greenhouse_agentic_management_design.md
    §45): a real deployment would replace this with human approval, task
    creation, or a robot/climate controller instead of mutating GreenhouseWorld
    directly. The management layer that decided the action is unaware of this.
    """
    if isinstance(action, WaterPlantAction):
        return _apply_water(world, action, config, day=day, timestamp=timestamp)
    if isinstance(action, HarvestPlantAction):
        return _apply_harvest(world, action, day=day, timestamp=timestamp)
    if isinstance(action, LowerPlantAction):
        return _apply_lower(world, action, day=day, timestamp=timestamp)
    return _apply_inspection(world, action, day=day, timestamp=timestamp)


def _apply_water(
    world: GreenhouseWorld,
    action: WaterPlantAction,
    config: ScenarioConfig,
    *,
    day: int,
    timestamp: datetime,
) -> tuple[GreenhouseWorld, Event]:
    plant = world.plant(action.plant_id)
    updated_plant = apply_irrigation(plant, action.amount_ml, config)
    world = _replace_plant(world, updated_plant)
    event = Event(
        event_id=f"evt_{world.greenhouse_id}_d{day}_{action.plant_id}_watering",
        greenhouse_id=world.greenhouse_id,
        plant_id=action.plant_id,
        simulated_day=day,
        timestamp=timestamp,
        event_type=EventType.WATERING,
        source=EventSource.RULE_BASED_POLICY,
        parameters={"amount_ml": action.amount_ml},
    )
    return world, event


def _apply_harvest(
    world: GreenhouseWorld, action: HarvestPlantAction, *, day: int, timestamp: datetime
) -> tuple[GreenhouseWorld, Event]:
    plant = world.plant(action.plant_id)
    harvested_mass_g = 0.0
    harvested_count = 0
    trusses = []
    for truss in plant.trusses:
        fruits = []
        for fruit in truss.fruits:
            if fruit.status == FruitStatus.RIPE:
                harvested_mass_g += fruit.mass_g
                harvested_count += 1
                fruits.append(fruit.model_copy(update={"status": FruitStatus.HARVESTED}))
            else:
                fruits.append(fruit)
        trusses.append(truss.model_copy(update={"fruits": fruits}))

    updated_plant = plant.model_copy(
        update={
            "trusses": trusses,
            "cumulative_harvest_g": plant.cumulative_harvest_g + harvested_mass_g,
        }
    )
    world = _replace_plant(world, updated_plant)
    event = Event(
        event_id=f"evt_{world.greenhouse_id}_d{day}_{action.plant_id}_harvest",
        greenhouse_id=world.greenhouse_id,
        plant_id=action.plant_id,
        simulated_day=day,
        timestamp=timestamp,
        event_type=EventType.HARVEST,
        source=EventSource.RULE_BASED_POLICY,
        parameters={"harvested_mass_g": harvested_mass_g, "harvested_fruit_count": harvested_count},
    )
    return world, event


def _apply_lower(
    world: GreenhouseWorld, action: LowerPlantAction, *, day: int, timestamp: datetime
) -> tuple[GreenhouseWorld, Event]:
    plant = world.plant(action.plant_id)
    updated_plant = plant.model_copy(
        update={"lowered_length_cm": plant.lowered_length_cm + action.amount_cm}
    )
    world = _replace_plant(world, updated_plant)
    event = Event(
        event_id=f"evt_{world.greenhouse_id}_d{day}_{action.plant_id}_lowering",
        greenhouse_id=world.greenhouse_id,
        plant_id=action.plant_id,
        simulated_day=day,
        timestamp=timestamp,
        event_type=EventType.LOWERING,
        source=EventSource.RULE_BASED_POLICY,
        parameters={"amount_cm": action.amount_cm},
    )
    return world, event


def _apply_inspection(
    world: GreenhouseWorld, action: ScheduleInspectionAction, *, day: int, timestamp: datetime
) -> tuple[GreenhouseWorld, Event]:
    event = Event(
        event_id=f"evt_{world.greenhouse_id}_d{day}_{action.plant_id}_inspection",
        greenhouse_id=world.greenhouse_id,
        plant_id=action.plant_id,
        simulated_day=day,
        timestamp=timestamp,
        event_type=EventType.MANUAL_INSPECTION,
        source=EventSource.RULE_BASED_POLICY,
        parameters={"reason": action.reason},
    )
    return world, event


def _replace_plant(world: GreenhouseWorld, updated_plant: PlantWorld) -> GreenhouseWorld:
    plants = [updated_plant if p.plant_id == updated_plant.plant_id else p for p in world.plants]
    return world.model_copy(update={"plants": plants})
