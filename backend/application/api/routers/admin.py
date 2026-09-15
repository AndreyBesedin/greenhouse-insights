"""Platform administration: users, platform-admin grants and the
platform-wide audit trail. Platform admins only."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from application.access_service import (
    AccessService,
    CannotRevokeOwnPlatformAdmin,
    SetPlatformAdminRequest,
    UserSummary,
)
from application.api.auth import get_actor
from application.api.dependencies import get_engine
from application.auth.actor import ActorContext
from application.auth.audit import AuditEvent

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_service(
    engine: Engine = Depends(get_engine), actor: ActorContext = Depends(get_actor)
) -> AccessService:
    return AccessService(engine, actor)


@router.get("/users")
def list_users(service: AccessService = Depends(_get_service)) -> list[UserSummary]:
    return service.list_users()


@router.put("/users/{user_id}/platform-admin")
def set_platform_admin(
    user_id: str,
    request: SetPlatformAdminRequest,
    service: AccessService = Depends(_get_service),
) -> UserSummary:
    try:
        user = service.set_platform_admin(user_id, request)
    except CannotRevokeOwnPlatformAdmin as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/audit")
def list_audit(service: AccessService = Depends(_get_service)) -> list[AuditEvent]:
    events = service.list_audit()
    assert events is not None  # platform-wide trail has no organization to be absent
    return events
