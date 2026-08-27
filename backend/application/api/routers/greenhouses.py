from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.greenhouse_service import GreenhouseDetail, GreenhouseListItem, GreenhouseService

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
