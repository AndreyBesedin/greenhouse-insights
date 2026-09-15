"""Who the current actor is and what they can reach: the tenant-facing
application service behind /me (and, later, organization and membership
administration)."""

from pydantic import BaseModel
from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.authorizer import Authorizer
from application.auth.models import OrganizationRole
from application.persistence.membership_repository import MembershipRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.user_repository import UserRepository


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


class AccessService:
    def __init__(self, engine: Engine, actor: ActorContext) -> None:
        self._actor = actor
        self._users = UserRepository(engine)
        self._organizations = OrganizationRepository(engine)
        self._memberships = MembershipRepository(engine)
        self._authorizer = Authorizer(self._memberships)

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
