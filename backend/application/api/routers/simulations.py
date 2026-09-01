from fastapi import APIRouter, Depends, HTTPException

from application.api.dependencies import get_simulation_service
from application.greenhouse_service import SimulationSummary
from application.simulation_service import SimulationService
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
    )
