from management.context import GreenhouseManagementContext
from management.validation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    WaterPlantAction,
)
from simulation.scenarios.config import ScenarioConfig


class DeterministicPolicy:
    """A simple rule-based operator: waters, harvests, and lowers plants that need it.

    Reads only observable plant state
    (docs/archive/design-history/greenhouse_agentic_management_design.md
    §21/§51: the baseline must use the same observable data the future agent
    gets, never hidden simulator truth), so it is a fair comparison point for
    AgenticPolicy under the same seed.
    """

    def decide(
        self, context: GreenhouseManagementContext, config: ScenarioConfig
    ) -> list[RequestedAction]:
        actions: list[RequestedAction] = []
        for plant in context.plant_states:
            if (
                plant.latest_soil_moisture_pct is not None
                and plant.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
            ):
                actions.append(
                    WaterPlantAction(plant_id=plant.plant_id, amount_ml=config.watering_amount_ml)
                )

            if (
                plant.latest_ripe_fruit_count is not None
                and plant.latest_ripe_fruit_count >= config.harvest_ripe_fruit_count_threshold
            ):
                actions.append(HarvestPlantAction(plant_id=plant.plant_id))

            if (
                plant.latest_visible_height_cm is not None
                and plant.latest_visible_height_cm > config.lower_plant_height_threshold_cm
            ):
                actions.append(
                    LowerPlantAction(
                        plant_id=plant.plant_id, amount_cm=config.lower_plant_amount_cm
                    )
                )

        return actions
