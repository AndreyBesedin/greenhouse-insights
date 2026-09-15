"""Who the current actor is, what they can reach, and the administration
of tenants: organizations, memberships and platform admins. Every
privileged mutation is authorized here and written to the audit trail
(docs/design/authentication_authorization_plan.md, "HTTP/API behavior";
docs/design/infrastructure_update_plan.md section 8)."""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.audit import AuditAction, AuditEvent
from application.auth.authorizer import Action, Authorizer, Forbidden
from application.auth.models import Organization, OrganizationMembership, OrganizationRole, User
from application.persistence.audit_repository import AuditRepository
from application.persistence.membership_repository import MembershipRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.user_repository import UserRepository

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OrganizationAccess(BaseModel):
    organization_id: str
    name: str
    slug: str
    # None for a platform admin, who reaches the organization without
    # being a member of it.
    role: OrganizationRole | None


class CurrentUser(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    is_platform_admin: bool
    organizations: list[OrganizationAccess]


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=60, pattern=_SLUG.pattern)


class Member(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    role: OrganizationRole


class SetMemberRequest(BaseModel):
    # The user must have signed in at least once; there is no invitation
    # flow yet (an open question in the plan).
    email: str = Field(min_length=3)
    role: OrganizationRole


class UserSummary(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    is_platform_admin: bool
    created_at: datetime


class SetPlatformAdminRequest(BaseModel):
    is_platform_admin: bool


class SlugTaken(Exception):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"an organization with slug {slug!r} already exists")


class UnknownUser(LookupError):
    pass


class AmbiguousEmail(Exception):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"more than one user has the email {email!r}; add by user id instead")


class CannotRevokeOwnPlatformAdmin(Exception):
    def __init__(self) -> None:
        super().__init__("a platform admin cannot revoke their own platform admin status")


class AccessService:
    def __init__(self, engine: Engine, actor: ActorContext) -> None:
        self._actor = actor
        self._users = UserRepository(engine)
        self._organizations = OrganizationRepository(engine)
        self._memberships = MembershipRepository(engine)
        self._audit = AuditRepository(engine)
        self._authorizer = Authorizer(self._memberships)

    # -- identity -------------------------------------------------------

    def current_user(self) -> CurrentUser:
        user = self._users.get(self._actor.actor_id)
        if user is None:
            raise LookupError(f"actor {self._actor.actor_id!r} has no user record")
        return CurrentUser(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            is_platform_admin=user.is_platform_admin,
            organizations=self.visible_organizations(),
        )

    def visible_organizations(self) -> list[OrganizationAccess]:
        """Every organization the actor may read, with their role in it."""
        memberships = {
            m.organization_id: m.role for m in self._memberships.list_for_user(self._actor.actor_id)
        }
        visible = self._authorizer.visible_organization_ids(self._actor)
        organizations = (
            self._organizations.list()
            if visible is None
            else self._organizations.list_by_ids(visible)
        )
        return [
            OrganizationAccess(
                organization_id=o.organization_id,
                name=o.name,
                slug=o.slug,
                role=memberships.get(o.organization_id),
            )
            for o in sorted(organizations, key=lambda o: o.name)
        ]

    # -- organizations (platform admin) ---------------------------------

    def create_organization(self, request: CreateOrganizationRequest) -> Organization:
        self._authorizer.require(self._actor, Action.ORGANIZATION_CREATE, None)
        if self._organizations.get_by_slug(request.slug) is not None:
            raise SlugTaken(request.slug)
        organization = Organization(
            organization_id=f"org_{uuid4().hex[:10]}",
            name=request.name,
            slug=request.slug,
            created_at=datetime.now(UTC),
        )
        self._organizations.save(organization)
        self._record(
            AuditAction.ORGANIZATION_CREATED,
            target_type="organization",
            target_id=organization.organization_id,
            organization_id=organization.organization_id,
            details={"name": organization.name, "slug": organization.slug},
        )
        return organization

    # -- memberships (organization admin) -------------------------------

    def list_members(self, organization_id: str) -> list[Member] | None:
        """None if the organization is absent or not visible to the actor."""
        if not self._visible(organization_id):
            return None
        self._authorizer.require(self._actor, Action.MEMBERSHIP_MANAGE, organization_id)
        members = []
        for membership in self._memberships.list_for_organization(organization_id):
            user = self._users.get(membership.user_id)
            if user is None:
                continue
            members.append(
                Member(
                    user_id=user.user_id,
                    email=user.email,
                    display_name=user.display_name,
                    role=membership.role,
                )
            )
        return sorted(members, key=lambda m: m.email)

    def set_member(self, organization_id: str, request: SetMemberRequest) -> Member | None:
        """Adds the user with `email` to the organization, or changes
        their role. None if the organization is absent or not visible."""
        if not self._visible(organization_id):
            return None
        self._authorizer.require(self._actor, Action.MEMBERSHIP_MANAGE, organization_id)
        user = self._user_by_email(request.email)
        previous = self._memberships.get(user.user_id, organization_id)
        self._memberships.save(
            OrganizationMembership(
                user_id=user.user_id,
                organization_id=organization_id,
                role=request.role,
                created_at=previous.created_at if previous else datetime.now(UTC),
            )
        )
        self._record(
            AuditAction.MEMBERSHIP_SET,
            target_type="membership",
            target_id=user.user_id,
            organization_id=organization_id,
            details={
                "email": user.email,
                "previous_role": previous.role.value if previous else None,
                "role": request.role.value,
            },
        )
        return Member(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            role=request.role,
        )

    def remove_member(self, organization_id: str, user_id: str) -> bool:
        """False if the organization or membership is absent (or the
        organization is not visible to the actor)."""
        if not self._visible(organization_id):
            return False
        self._authorizer.require(self._actor, Action.MEMBERSHIP_MANAGE, organization_id)
        membership = self._memberships.get(user_id, organization_id)
        if membership is None:
            return False
        self._memberships.delete(user_id, organization_id)
        self._record(
            AuditAction.MEMBERSHIP_REMOVED,
            target_type="membership",
            target_id=user_id,
            organization_id=organization_id,
            details={"previous_role": membership.role.value},
        )
        return True

    # -- users (platform admin) -----------------------------------------

    def list_users(self) -> list[UserSummary]:
        self._authorizer.require(self._actor, Action.PLATFORM_ADMINISTER, None)
        return [_user_summary(user) for user in sorted(self._users.list(), key=lambda u: u.email)]

    def set_platform_admin(
        self, user_id: str, request: SetPlatformAdminRequest
    ) -> UserSummary | None:
        """Grants or revokes platform admin. Only a platform admin may do
        this, never to themselves (so the last admin cannot lock everyone
        out by accident). None if the user does not exist."""
        self._authorizer.require(self._actor, Action.PLATFORM_ADMINISTER, None)
        user = self._users.get(user_id)
        if user is None:
            return None
        if user.user_id == self._actor.actor_id and not request.is_platform_admin:
            raise CannotRevokeOwnPlatformAdmin()
        if user.is_platform_admin != request.is_platform_admin:
            user = user.model_copy(update={"is_platform_admin": request.is_platform_admin})
            self._users.save(user)
            self._record(
                AuditAction.PLATFORM_ADMIN_GRANTED
                if request.is_platform_admin
                else AuditAction.PLATFORM_ADMIN_REVOKED,
                target_type="user",
                target_id=user.user_id,
                details={"email": user.email},
            )
        return _user_summary(user)

    # -- audit ----------------------------------------------------------

    def list_audit(self, organization_id: str | None = None) -> list[AuditEvent] | None:
        """The platform-wide trail for a platform admin, or one
        organization's trail for its admins. None if the organization is
        absent or not visible."""
        if organization_id is None:
            self._authorizer.require(self._actor, Action.PLATFORM_ADMINISTER, None)
            return self._audit.list_recent()
        if not self._visible(organization_id):
            return None
        self._authorizer.require(self._actor, Action.AUDIT_READ, organization_id)
        return self._audit.list_for_organization(organization_id)

    # -- helpers --------------------------------------------------------

    def _visible(self, organization_id: str) -> bool:
        if self._organizations.get(organization_id) is None:
            return False
        return self._authorizer.can(self._actor, Action.ORGANIZATION_READ, organization_id)

    def _user_by_email(self, email: str) -> User:
        matches = [u for u in self._users.list() if u.email.lower() == email.strip().lower()]
        if not matches:
            raise UnknownUser(f"no user with email {email!r} has signed in yet")
        if len(matches) > 1:
            raise AmbiguousEmail(email)
        return matches[0]

    def _record(
        self,
        action: AuditAction,
        *,
        target_type: str,
        target_id: str,
        organization_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit.append(
            AuditEvent(
                audit_id=f"aud_{uuid4().hex[:12]}",
                timestamp=datetime.now(UTC),
                actor_id=self._actor.actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                organization_id=organization_id,
                details=details or {},
            )
        )


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_platform_admin=user.is_platform_admin,
        created_at=user.created_at,
    )


__all__ = [
    "AccessService",
    "AmbiguousEmail",
    "CannotRevokeOwnPlatformAdmin",
    "CreateOrganizationRequest",
    "CurrentUser",
    "Forbidden",
    "Member",
    "OrganizationAccess",
    "SetMemberRequest",
    "SetPlatformAdminRequest",
    "SlugTaken",
    "UnknownUser",
    "UserSummary",
]
