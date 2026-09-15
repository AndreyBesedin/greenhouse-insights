"""The tenant-isolation rules enforced by GreenhouseService itself, with
no HTTP in the loop: a CLI, worker or agent going through the service
gets exactly the same answers (docs/design/authentication_authorization_plan.md
section 6)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.audit import AuditAction
from application.auth.authorizer import Forbidden
from application.auth.models import OrganizationRole
from application.greenhouse_service import (
    AssignOrganizationRequest,
    CreateGreenhouseRequest,
    GreenhouseService,
    UnknownOrganization,
)
from application.persistence.audit_repository import AuditRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from domain.enums import SourceType
from tests.application.support import ROOT, greenhouse, member, organization


@pytest.fixture
def two_tenants(engine: Engine) -> dict[str, ActorContext]:
    organization(engine, "org_a")
    organization(engine, "org_b")
    greenhouse(engine, "gh_a", "org_a")
    greenhouse(engine, "gh_b", "org_b")
    return {
        "viewer_a": member(engine, "viewer-a", "org_a", OrganizationRole.VIEWER),
        "editor_a": member(engine, "editor-a", "org_a", OrganizationRole.EDITOR),
        "admin_a": member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN),
        "admin_b": member(engine, "admin-b", "org_b", OrganizationRole.ORGANIZATION_ADMIN),
        "nobody": ActorContext.user("user_nobody"),
    }


def _create_request() -> CreateGreenhouseRequest:
    return CreateGreenhouseRequest(
        name="New",
        organization_id="org_a",
        source_type=SourceType.SIMULATION,
        crop="cherry_tomato",
        rows=1,
        columns=1,
        duration_days=2,
    )


def test_list_shows_only_the_actors_organizations(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    def ids(actor: ActorContext) -> set[str]:
        return {g.greenhouse_id for g in GreenhouseService(engine, actor).list_greenhouses()}

    assert ids(two_tenants["viewer_a"]) == {"gh_a"}
    assert ids(two_tenants["admin_b"]) == {"gh_b"}
    assert ids(two_tenants["nobody"]) == set()
    assert ids(ROOT) >= {"gh_a", "gh_b"}


def test_another_tenants_greenhouse_is_absent_not_forbidden(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    """Guessing an identifier must not even confirm it exists."""
    service = GreenhouseService(engine, two_tenants["admin_b"])
    now = datetime(2026, 6, 1, tzinfo=UTC)

    assert service.get_greenhouse_detail("gh_a") is None
    assert service.get_state("gh_a", at=None) is None
    assert service.get_timeline("gh_a") is None
    assert service.get_management_history("gh_a") is None
    assert service.get_plant_detail("gh_a", "gh_a_plant_001", at=None) is None
    assert service.get_plant_history("gh_a", "gh_a_plant_001", up_to=now) is None
    assert service.get_greenhouse_detail("gh_b") is not None


def test_a_viewer_can_read_their_own_tenant(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    service = GreenhouseService(engine, two_tenants["viewer_a"])

    detail = service.get_greenhouse_detail("gh_a")

    assert detail is not None
    assert service.get_timeline("gh_a") is not None


def test_platform_admin_reaches_every_tenant(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.get_greenhouse_detail("gh_a") is not None
    assert service.get_greenhouse_detail("gh_b") is not None


@pytest.mark.parametrize("who", ["viewer_a", "editor_a", "admin_a"])
def test_only_a_platform_admin_creates_greenhouses(
    engine: Engine, two_tenants: dict[str, ActorContext], who: str
) -> None:
    with pytest.raises(Forbidden):
        GreenhouseService(engine, two_tenants[who]).create_greenhouse(_create_request())

    assert all(g.name != "New" for g in GreenhouseRepository(engine).list())


def test_platform_admin_creates_a_greenhouse_in_any_organization(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    detail = GreenhouseService(engine, ROOT).create_greenhouse(_create_request())

    assert detail.greenhouse.organization_id == "org_a"


def test_delete_is_forbidden_for_an_organization_admin_and_absent_for_outsiders(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    with pytest.raises(Forbidden):
        GreenhouseService(engine, two_tenants["admin_a"]).delete_greenhouse("gh_a")
    assert GreenhouseService(engine, two_tenants["admin_b"]).delete_greenhouse("gh_a") is False
    assert GreenhouseRepository(engine).get("gh_a") is not None

    assert GreenhouseService(engine, ROOT).delete_greenhouse("gh_a") is True
    assert GreenhouseRepository(engine).get("gh_a") is None


def test_platform_admin_moves_a_greenhouse_between_organizations_with_audit(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    detail = GreenhouseService(engine, ROOT).assign_organization(
        "gh_a", AssignOrganizationRequest(organization_id="org_b")
    )

    assert detail is not None and detail.greenhouse.organization_id == "org_b"
    assert GreenhouseService(engine, two_tenants["admin_b"]).get_greenhouse_detail("gh_a")
    assert GreenhouseService(engine, two_tenants["admin_a"]).get_greenhouse_detail("gh_a") is None
    trail = AuditRepository(engine).list_for_organization("org_b")
    assert [(e.action, e.details) for e in trail] == [
        (AuditAction.GREENHOUSE_REASSIGNED, {"previous_organization_id": "org_a"})
    ]


def test_reassigning_needs_a_platform_admin_and_a_real_organization(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    with pytest.raises(Forbidden):
        GreenhouseService(engine, two_tenants["admin_a"]).assign_organization(
            "gh_a", AssignOrganizationRequest(organization_id="org_b")
        )
    assert (
        GreenhouseService(engine, two_tenants["admin_b"]).assign_organization(
            "gh_a", AssignOrganizationRequest(organization_id="org_b")
        )
        is None
    )
    with pytest.raises(UnknownOrganization):
        GreenhouseService(engine, ROOT).assign_organization(
            "gh_a", AssignOrganizationRequest(organization_id="org_nope")
        )
    stored = GreenhouseRepository(engine).get("gh_a")
    assert stored is not None and stored.organization_id == "org_a"


def test_creating_and_deleting_greenhouses_is_audited(
    engine: Engine, two_tenants: dict[str, ActorContext]
) -> None:
    service = GreenhouseService(engine, ROOT)
    created = service.create_greenhouse(_create_request()).greenhouse
    service.delete_greenhouse(created.greenhouse_id)

    trail = [
        e for e in AuditRepository(engine).list_recent() if e.target_id == created.greenhouse_id
    ]
    assert [e.action for e in trail] == [
        AuditAction.GREENHOUSE_DELETED,
        AuditAction.GREENHOUSE_CREATED,
    ]
    assert all(e.organization_id == "org_a" and e.actor_id == ROOT.actor_id for e in trail)
