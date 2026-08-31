from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from domain.enums import EventSource, EventType, FruitStatus
from domain.event import Event
from domain.world import GreenhouseWorld, PlantWorld
from simulation.dynamics.water import apply_irrigation
from simulation.scenarios.config import ScenarioConfig


class WaterPlantAction(BaseModel):
    action_type: Literal["WATER_PLANT"] = "WATER_PLANT"
    plant_id: str
    amount_ml: float


class HarvestPlantAction(BaseModel):
    action_type: Literal["HARVEST_PLANT"] = "HARVEST_PLANT"
    plant_id: str


class LowerPlantAction(BaseModel):
    action_type: Literal["LOWER_PLANT"] = "LOWER_PLANT"
    plant_id: str
    amount_cm: float


class ScheduleInspectionAction(BaseModel):
    action_type: Literal["SCHEDULE_INSPECTION"] = "SCHEDULE_INSPECTION"
    plant_id: str
    reason: str


RequestedAction = (
    WaterPlantAction | HarvestPlantAction | LowerPlantAction | ScheduleInspectionAction
)

_MAX_WATER_AMOUNT_ML = 2000.0


class ActionResult(BaseModel):
    accepted: bool
    reason: str | None = None


def validate_action(world: GreenhouseWorld, action: RequestedAction) -> ActionResult:
    try:
        plant = world.plant(action.plant_id)
    except LookupError:
        return ActionResult(accepted=False, reason=f"plant {action.plant_id!r} does not exist")

    if isinstance(action, WaterPlantAction):
        if not (0 < action.amount_ml <= _MAX_WATER_AMOUNT_ML):
            return ActionResult(accepted=False, reason="water amount out of range")
    elif isinstance(action, LowerPlantAction):
        visible_height = plant.stem_length_cm - plant.lowered_length_cm
        if not (0 < action.amount_cm <= visible_height):
            return ActionResult(accepted=False, reason="lowering amount exceeds visible height")
    elif isinstance(action, ScheduleInspectionAction):
        if not action.reason.strip():
            return ActionResult(accepted=False, reason="inspection reason is required")

    return ActionResult(accepted=True)


def apply_action(
    world: GreenhouseWorld,
    action: RequestedAction,
    config: ScenarioConfig,
    *,
    day: int,
    timestamp: datetime,
) -> tuple[GreenhouseWorld, Event]:
    """Applies an already-validated action, returning the updated world and its Event."""
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
