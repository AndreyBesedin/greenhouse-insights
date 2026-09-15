"""The authorization rules, in one boring place.

A platform admin may do everything. Everyone else acts inside the
organizations they are a member of, and what they may do there is set by
their role in that organization - roles nest, so an editor may do
everything a viewer may, and an organization admin everything an editor
may. Some actions (creating and deleting greenhouses, platform
administration) are platform-admin only for now
(docs/design/authentication_authorization_plan.md, "OrganizationMembership"
and "Authorization in application services").

Deliberately not a policy language: a new rule is a new Action member and
one entry in the table below.
"""

from enum import StrEnum
from typing import Protocol

from application.auth.actor import ActorContext
from application.auth.models import OrganizationMembership, OrganizationRole


class Action(StrEnum):
    ORGANIZATION_READ = "ORGANIZATION_READ"
    GREENHOUSE_READ = "GREENHOUSE_READ"
    GREENHOUSE_WRITE = "GREENHOUSE_WRITE"
    GREENHOUSE_CREATE = "GREENHOUSE_CREATE"
    GREENHOUSE_DELETE = "GREENHOUSE_DELETE"
    GREENHOUSE_ASSIGN = "GREENHOUSE_ASSIGN"
    MEMBERSHIP_MANAGE = "MEMBERSHIP_MANAGE"
    ORGANIZATION_CREATE = "ORGANIZATION_CREATE"
    AUDIT_READ = "AUDIT_READ"
    PLATFORM_ADMINISTER = "PLATFORM_ADMINISTER"


# The smallest organization role that permits an action inside that
# organization; None means no role does and only a platform admin may.
_MINIMUM_ROLE: dict[Action, OrganizationRole | None] = {
    Action.ORGANIZATION_READ: OrganizationRole.VIEWER,
    Action.GREENHOUSE_READ: OrganizationRole.VIEWER,
    Action.GREENHOUSE_WRITE: OrganizationRole.EDITOR,
    Action.GREENHOUSE_CREATE: None,
    Action.GREENHOUSE_DELETE: None,
    Action.GREENHOUSE_ASSIGN: None,
    Action.MEMBERSHIP_MANAGE: OrganizationRole.ORGANIZATION_ADMIN,
    Action.ORGANIZATION_CREATE: None,
    # Organization admins read their own organization's trail.
    Action.AUDIT_READ: OrganizationRole.ORGANIZATION_ADMIN,
    Action.PLATFORM_ADMINISTER: None,
}

_ROLE_RANK: dict[OrganizationRole, int] = {
    OrganizationRole.VIEWER: 0,
    OrganizationRole.EDITOR: 1,
    OrganizationRole.ORGANIZATION_ADMIN: 2,
}


class Forbidden(Exception):
    """The actor is known but may not perform this action on this
    organization's resources."""

    def __init__(self, actor: ActorContext, action: Action, organization_id: str | None) -> None:
        self.actor = actor
        self.action = action
        self.organization_id = organization_id
        where = f" in organization {organization_id!r}" if organization_id is not None else ""
        super().__init__(f"actor {actor.actor_id!r} may not {action.value}{where}")


class MembershipLookup(Protocol):
    """What the authorizer needs from persistence - MembershipRepository
    satisfies it; tests can pass something in-memory."""

    def get(self, user_id: str, organization_id: str) -> OrganizationMembership | None: ...

    def list_for_user(self, user_id: str) -> list[OrganizationMembership]: ...


def role_permits(role: OrganizationRole | None, action: Action) -> bool:
    minimum = _MINIMUM_ROLE[action]
    if minimum is None or role is None:
        return False
    return _ROLE_RANK[role] >= _ROLE_RANK[minimum]


class Authorizer:
    def __init__(self, memberships: MembershipLookup) -> None:
        self._memberships = memberships

    def role_in(self, actor: ActorContext, organization_id: str) -> OrganizationRole | None:
        membership = self._memberships.get(actor.actor_id, organization_id)
        return None if membership is None else membership.role

    def can(self, actor: ActorContext, action: Action, organization_id: str | None) -> bool:
        """Whether `actor` may perform `action` on resources of
        `organization_id` (None for platform-wide actions with no
        organization, which only a platform admin may perform)."""
        if actor.is_platform_admin:
            return True
        if organization_id is None:
            return False
        return role_permits(self.role_in(actor, organization_id), action)

    def require(self, actor: ActorContext, action: Action, organization_id: str | None) -> None:
        if not self.can(actor, action, organization_id):
            raise Forbidden(actor, action, organization_id)

    def visible_organization_ids(self, actor: ActorContext) -> list[str] | None:
        """The organizations whose resources the actor may read; None
        when there is no restriction (platform admin sees every tenant)."""
        if actor.is_platform_admin:
            return None
        return [m.organization_id for m in self._memberships.list_for_user(actor.actor_id)]
