from typing import Literal

from pydantic import BaseModel

from domain.world import GreenhouseWorld

MAX_WATER_AMOUNT_ML = 2000.0


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


class ActionResult(BaseModel):
    accepted: bool
    reason: str | None = None


def validate_action(world: GreenhouseWorld, action: RequestedAction) -> ActionResult:
    """Checks a requested action against real system state before execution.

    This is a hard-constraint check
    (docs/archive/design-history/greenhouse_agentic_management_design.md
    §18-19), independent of which policy proposed the action or how it will be
    executed. `world` stands in for "current real system state" - in a real
    deployment this would be live sensor/controller state instead of the
    simulator's GreenhouseWorld, but the check itself is the same.
    """
    try:
        plant = world.plant(action.plant_id)
    except LookupError:
        return ActionResult(accepted=False, reason=f"plant {action.plant_id!r} does not exist")

    if isinstance(action, WaterPlantAction):
        if not (0 < action.amount_ml <= MAX_WATER_AMOUNT_ML):
            return ActionResult(accepted=False, reason="water amount out of range")
    elif isinstance(action, LowerPlantAction):
        visible_height = plant.stem_length_cm - plant.lowered_length_cm
        if not (0 < action.amount_cm <= visible_height):
            return ActionResult(accepted=False, reason="lowering amount exceeds visible height")
    elif isinstance(action, ScheduleInspectionAction):
        if not action.reason.strip():
            return ActionResult(accepted=False, reason="inspection reason is required")

    return ActionResult(accepted=True)
