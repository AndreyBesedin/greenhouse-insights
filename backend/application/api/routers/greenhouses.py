from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from application.api.dependencies import get_engine, get_simulation_service
from application.greenhouse_service import (
    CreateGreenhouseRequest,
    GreenhouseDetail,
    GreenhouseListItem,
    GreenhouseService,
    PlantDetail,
    TimelineSummary,
)
from application.simulation_service import SimulationService
from domain.management_trace import ManagementTrace
from domain.state import GreenhouseState, PlantState

router = APIRouter(prefix="/greenhouses", tags=["greenhouses"])


def _get_service(engine: Engine = Depends(get_engine)) -> GreenhouseService:
    return GreenhouseService(engine)


@router.get("")
def list_greenhouses(
    service: GreenhouseService = Depends(_get_service),
) -> list[GreenhouseListItem]:
    return service.list_greenhouses()


@router.post("", status_code=201)
def create_greenhouse(
    request: CreateGreenhouseRequest, service: GreenhouseService = Depends(_get_service)
) -> GreenhouseDetail:
    return service.create_greenhouse(request)


@router.get("/{greenhouse_id}")
def get_greenhouse(
    greenhouse_id: str, service: GreenhouseService = Depends(_get_service)
) -> GreenhouseDetail:
    detail = service.get_greenhouse_detail(greenhouse_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="greenhouse not found")
    return detail


@router.delete("/{greenhouse_id}", status_code=204)
def delete_greenhouse(
    greenhouse_id: str,
    service: GreenhouseService = Depends(_get_service),
    simulation_service: SimulationService = Depends(get_simulation_service),
) -> None:
    detail = service.get_greenhouse_detail(greenhouse_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="greenhouse not found")
    if detail.simulation is not None:
        simulation_service.cancel(detail.simulation.simulation_id)
    service.delete_greenhouse(greenhouse_id)


@router.get("/{greenhouse_id}/state")
def get_state(
    greenhouse_id: str,
    day: int | None = None,
    service: GreenhouseService = Depends(_get_service),
) -> GreenhouseState:
    state = service.get_state(greenhouse_id, day=day)
    if state is None:
        raise HTTPException(status_code=404, detail="no state snapshot found")
    return state


@router.get("/{greenhouse_id}/plants/{plant_id}")
def get_plant(
    greenhouse_id: str,
    plant_id: str,
    day: int | None = None,
    service: GreenhouseService = Depends(_get_service),
) -> PlantDetail:
    detail = service.get_plant_detail(greenhouse_id, plant_id, day=day)
    if detail is None:
        raise HTTPException(status_code=404, detail="plant not found")
    return detail


@router.get("/{greenhouse_id}/plants/{plant_id}/history")
def get_plant_history(
    greenhouse_id: str,
    plant_id: str,
    up_to_day: int,
    service: GreenhouseService = Depends(_get_service),
) -> list[PlantState]:
    history = service.get_plant_history(greenhouse_id, plant_id, up_to_day=up_to_day)
    if history is None:
        raise HTTPException(status_code=404, detail="plant not found")
    return history


@router.get("/{greenhouse_id}/timeline")
def get_timeline(
    greenhouse_id: str, service: GreenhouseService = Depends(_get_service)
) -> TimelineSummary:
    timeline = service.get_timeline(greenhouse_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="greenhouse not found")
    return timeline


@router.get("/{greenhouse_id}/management/history")
def get_management_history(
    greenhouse_id: str, service: GreenhouseService = Depends(_get_service)
) -> list[ManagementTrace]:
    history = service.get_management_history(greenhouse_id)
    if history is None:
        raise HTTPException(status_code=404, detail="greenhouse not found")
    return history
