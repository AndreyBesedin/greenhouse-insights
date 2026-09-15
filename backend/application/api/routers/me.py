from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from application.access_service import AccessService, CurrentUser
from application.api.auth import get_actor
from application.api.dependencies import get_engine
from application.auth.actor import ActorContext

router = APIRouter(prefix="/me", tags=["me"])


def _get_service(
    engine: Engine = Depends(get_engine), actor: ActorContext = Depends(get_actor)
) -> AccessService:
    return AccessService(engine, actor)


@router.get("")
def get_current_user(service: AccessService = Depends(_get_service)) -> CurrentUser:
    """The authenticated user and the organizations they can reach."""
    return service.current_user()
