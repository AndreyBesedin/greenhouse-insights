from typing import Protocol

from domain.enums import FruitStatus
from domain.world import GreenhouseWorld
from simulation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    WaterPlantAction,
)
from simulation.scenarios.config import ScenarioConfig


class ManagementPolicy(Protocol):
    def decide(self, world: GreenhouseWorld, config: ScenarioConfig) -> list[RequestedAction]: ...


class NoOpPolicy:
    def decide(self, world: GreenhouseWorld, config: ScenarioConfig) -> list[RequestedAction]:
        return []


class DeterministicPolicy:
    """A simple rule-based operator: waters, harvests, and lowers plants that need it.

    This is the simulation's own built-in "autopilot", not the
    GreenhouseManagementContext-based policy from the agentic-management design
    doc — that richer context boundary belongs to V1, once an actual agent needs
    it.
    """

    def decide(self, world: GreenhouseWorld, config: ScenarioConfig) -> list[RequestedAction]:
        actions: list[RequestedAction] = []
        for plant in world.plants:
            reservoir_pct = 100.0 * plant.water_reservoir_ml / config.water_capacity_ml
            if reservoir_pct < config.watering_trigger_reservoir_pct:
                actions.append(
                    WaterPlantAction(plant_id=plant.plant_id, amount_ml=config.watering_amount_ml)
                )

            ripe_count = sum(
                1
                for truss in plant.trusses
                for fruit in truss.fruits
                if fruit.status == FruitStatus.RIPE
            )
            if ripe_count >= config.harvest_ripe_fruit_count_threshold:
                actions.append(HarvestPlantAction(plant_id=plant.plant_id))

            visible_height = plant.stem_length_cm - plant.lowered_length_cm
            if visible_height > config.lower_plant_height_threshold_cm:
                actions.append(
                    LowerPlantAction(
                        plant_id=plant.plant_id, amount_cm=config.lower_plant_amount_cm
                    )
                )

        return actions
