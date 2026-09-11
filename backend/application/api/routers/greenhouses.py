from datetime import datetime

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
from application.simulation_service import ManualActionNotAllowed, SimulationService
from domain.management_trace import ManagementTrace
from domain.recommendation import Recommendation
from domain.state import GreenhouseState, PlantState
from management.validation.actions import RequestedAction

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
    at: datetime | None = None,
    service: GreenhouseService = Depends(_get_service),
) -> GreenhouseState:
    """The greenhouse as of `at` (ISO-8601, timezone-aware): the latest
    snapshot taken at or before it. Omit `at` for the latest snapshot."""
    state = service.get_state(greenhouse_id, at=at)
    if state is None:
        raise HTTPException(status_code=404, detail="no state snapshot found")
    return state


@router.get("/{greenhouse_id}/plants/{plant_id}")
def get_plant(
    greenhouse_id: str,
    plant_id: str,
    at: datetime | None = None,
    service: GreenhouseService = Depends(_get_service),
) -> PlantDetail:
    detail = service.get_plant_detail(greenhouse_id, plant_id, at=at)
    if detail is None:
        raise HTTPException(status_code=404, detail="plant not found")
    return detail


@router.get("/{greenhouse_id}/plants/{plant_id}/history")
def get_plant_history(
    greenhouse_id: str,
    plant_id: str,
    up_to: datetime,
    service: GreenhouseService = Depends(_get_service),
) -> list[PlantState]:
    history = service.get_plant_history(greenhouse_id, plant_id, up_to=up_to)
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


@router.get("/{greenhouse_id}/recommendations")
def get_recommendations(
    greenhouse_id: str,
    at: datetime,
    simulation_service: SimulationService = Depends(get_simulation_service),
) -> list[Recommendation]:
    """Recommendations made against the state snapshot taken at `at`."""
    return simulation_service.list_recommendations(greenhouse_id, at)


@router.post("/{greenhouse_id}/recommendations/approve-all")
async def approve_all_recommendations(
    greenhouse_id: str,
    at: datetime,
    simulation_service: SimulationService = Depends(get_simulation_service),
) -> list[Recommendation]:
    return await simulation_service.approve_all_pending(greenhouse_id, at)


@router.post("/{greenhouse_id}/plants/{plant_id}/actions", status_code=201)
async def submit_manual_action(
    greenhouse_id: str,
    plant_id: str,
    action: RequestedAction,
    simulation_service: SimulationService = Depends(get_simulation_service),
) -> Recommendation:
    if action.plant_id != plant_id:
        raise HTTPException(status_code=422, detail="action plant_id must match the URL")
    try:
        return await simulation_service.submit_manual_action(greenhouse_id, action)
    except ManualActionNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
