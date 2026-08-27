from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.greenhouse_service import (
    GreenhouseDetail,
    GreenhouseListItem,
    GreenhouseService,
    PlantDetail,
)
from domain.state import GreenhouseState

router = APIRouter(prefix="/greenhouses", tags=["greenhouses"])


def _get_service(engine: Engine = Depends(get_engine)) -> GreenhouseService:
    return GreenhouseService(engine)


@router.get("")
def list_greenhouses(
    service: GreenhouseService = Depends(_get_service),
) -> list[GreenhouseListItem]:
    return service.list_greenhouses()


@router.get("/{greenhouse_id}")
def get_greenhouse(
    greenhouse_id: str, service: GreenhouseService = Depends(_get_service)
) -> GreenhouseDetail:
    detail = service.get_greenhouse_detail(greenhouse_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="greenhouse not found")
    return detail


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
