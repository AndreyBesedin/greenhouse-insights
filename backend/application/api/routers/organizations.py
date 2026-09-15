from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine

from application.access_service import (
    AccessService,
    AmbiguousEmail,
    CreateOrganizationRequest,
    Member,
    OrganizationAccess,
    SetMemberRequest,
    SlugTaken,
    UnknownUser,
)
from application.api.auth import get_actor
from application.api.dependencies import get_engine
from application.auth.actor import ActorContext
from application.auth.audit import AuditEvent
from application.auth.models import Organization

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _get_service(
    engine: Engine = Depends(get_engine), actor: ActorContext = Depends(get_actor)
) -> AccessService:
    return AccessService(engine, actor)


@router.get("")
def list_organizations(service: AccessService = Depends(_get_service)) -> list[OrganizationAccess]:
    """The organizations the current user can reach, with their role."""
    return service.visible_organizations()


@router.post("", status_code=201)
def create_organization(
    request: CreateOrganizationRequest, service: AccessService = Depends(_get_service)
) -> Organization:
    try:
        return service.create_organization(request)
    except SlugTaken as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{organization_id}/members")
def list_members(
    organization_id: str, service: AccessService = Depends(_get_service)
) -> list[Member]:
    members = service.list_members(organization_id)
    if members is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return members


@router.put("/{organization_id}/members")
def set_member(
    organization_id: str,
    request: SetMemberRequest,
    service: AccessService = Depends(_get_service),
) -> Member:
    """Adds a user (by the email they signed in with) to the organization,
    or changes their role."""
    try:
        member = service.set_member(organization_id, request)
    except UnknownUser as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AmbiguousEmail as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if member is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return member


@router.delete("/{organization_id}/members/{user_id}", status_code=204)
def remove_member(
    organization_id: str, user_id: str, service: AccessService = Depends(_get_service)
) -> None:
    if not service.remove_member(organization_id, user_id):
        raise HTTPException(status_code=404, detail="membership not found")


@router.get("/{organization_id}/audit")
def list_organization_audit(
    organization_id: str, service: AccessService = Depends(_get_service)
) -> list[AuditEvent]:
    events = service.list_audit(organization_id)
    if events is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return events
