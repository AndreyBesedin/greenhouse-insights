from fastapi import APIRouter, Depends, HTTPException

from application.api.dependencies import get_simulation_service
from application.greenhouse_service import SimulationSummary
from application.simulation_service import PendingRecommendationsExist, SimulationService
from domain.management_progress import ManagementProgress
from simulation.definitions import SimulationDefinition

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/{simulation_id}/run")
async def run_simulation(
    simulation_id: str, service: SimulationService = Depends(get_simulation_service)
) -> SimulationSummary:
    definition = await service.start_simulation(simulation_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="simulation not found")
    return _to_summary(definition)


@router.post("/{simulation_id}/next-day")
async def advance_simulation_one_day(
    simulation_id: str,
    confirm_dismiss_remaining: bool = False,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationSummary:
    try:
        definition = await service.advance_one_day(
            simulation_id, confirm_dismiss_remaining=confirm_dismiss_remaining
        )
    except PendingRecommendationsExist as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if definition is None:
        raise HTTPException(status_code=404, detail="simulation not found")
    return _to_summary(definition)


@router.get("/{simulation_id}/management-progress")
def get_management_progress(
    simulation_id: str, service: SimulationService = Depends(get_simulation_service)
) -> ManagementProgress | None:
    return service.get_management_progress(simulation_id)


@router.get("/{simulation_id}/status")
def get_simulation_status(
    simulation_id: str, service: SimulationService = Depends(get_simulation_service)
) -> SimulationSummary:
    definition = service.get_status(simulation_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="simulation not found")
    return _to_summary(definition)


def _to_summary(definition: SimulationDefinition) -> SimulationSummary:
    return SimulationSummary(
        simulation_id=definition.simulation_id,
        status=definition.status,
        current_step=definition.current_step,
        total_steps=definition.total_steps,
        management_policy=definition.management_policy,
        action_executor=definition.action_executor,
    )
