"""Shared helpers for application-layer tests: a platform-admin actor for
tests that are not about authorization, and dev-mode HTTP identities."""

from datetime import UTC, datetime

from sqlalchemy import Engine

from application.api.auth import AuthMode, AuthSettings, get_auth_settings
from application.api.main import app
from application.auth.actor import ActorContext
from application.auth.identity import DevHeaderAuthenticator, UserResolver, actor_for
from application.auth.models import Organization, OrganizationMembership, OrganizationRole
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.membership_repository import MembershipRepository
from application.persistence.organization_repository import OrganizationRepository
from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, build_grid_plants

FIXTURE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

# The dev-mode subject the API test clients send by default.
ADMIN_SUBJECT = "dev-admin"
ADMIN_HEADERS = {"X-Dev-Subject": ADMIN_SUBJECT}

# For service-level tests of behaviour other than authorization.
ROOT = ActorContext.user("user_root", is_platform_admin=True)


def install_dev_auth(*, platform_admin_subjects: tuple[str, ...] = (ADMIN_SUBJECT,)) -> None:
    app.dependency_overrides[get_auth_settings] = lambda: AuthSettings(
        mode=AuthMode.DEV, platform_admin_subjects=frozenset(platform_admin_subjects)
    )


def as_user(subject: str) -> dict[str, str]:
    return {"X-Dev-Subject": subject}


def organization(engine: Engine, organization_id: str) -> Organization:
    org = Organization(
        organization_id=organization_id,
        name=organization_id.removeprefix("org_").title(),
        slug=organization_id.removeprefix("org_"),
        created_at=FIXTURE_TIME,
    )
    OrganizationRepository(engine).save(org)
    return org


def member(
    engine: Engine, subject: str, organization_id: str, role: OrganizationRole
) -> ActorContext:
    """A dev-mode user (created as they would be on first login) with one
    membership; send `as_user(subject)` to act as them over HTTP, or use
    the returned actor at the service level."""
    user = UserResolver(engine, platform_admin_subjects=frozenset()).resolve(
        DevHeaderAuthenticator().authenticate({"x-dev-subject": subject})
    )
    MembershipRepository(engine).save(
        OrganizationMembership(
            user_id=user.user_id,
            organization_id=organization_id,
            role=role,
            created_at=FIXTURE_TIME,
        )
    )
    return actor_for(user)


def greenhouse(engine: Engine, greenhouse_id: str, organization_id: str) -> Greenhouse:
    """A minimal greenhouse owned by `organization_id`, saved directly
    through the repository (privileged setup, no actor)."""
    gh = Greenhouse(
        greenhouse_id=greenhouse_id,
        organization_id=organization_id,
        name=greenhouse_id,
        description="",
        source_type=SourceType.SIMULATION,
        crop="cherry_tomato",
        layout=GreenhouseLayout(rows=1, columns=1),
        plants=build_grid_plants(greenhouse_id, "cherry_tomato", 1, 1),
        created_at=FIXTURE_TIME,
    )
    GreenhouseRepository(engine).save(gh)
    return gh
