"""Tenant administration through AccessService: organizations,
memberships, platform admins and the audit trail, with the same rules
whoever calls."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from application.access_service import (
    AccessService,
    AmbiguousEmail,
    CannotRevokeOwnPlatformAdmin,
    CreateOrganizationRequest,
    SetMemberRequest,
    SetPlatformAdminRequest,
    SlugTaken,
    UnknownUser,
)
from application.auth.actor import ActorContext
from application.auth.audit import AuditAction
from application.auth.authorizer import Forbidden
from application.auth.identity import (
    BOOTSTRAP_ACTOR_ID,
    AuthenticatedIdentity,
    UserResolver,
    actor_for,
)
from application.auth.models import OrganizationRole, User
from application.persistence.audit_repository import AuditRepository
from application.persistence.membership_repository import MembershipRepository
from application.persistence.user_repository import UserRepository
from tests.application.support import ROOT, member, organization


@pytest.fixture
def root_user(engine: Engine) -> ActorContext:
    """ROOT as a real user row, so self-revocation can be tested."""
    UserRepository(engine).save(
        User(
            user_id=ROOT.actor_id,
            auth_subject="root",
            email="root@dev.local",
            is_platform_admin=True,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    return ROOT


def _signed_in(engine: Engine, subject: str) -> ActorContext:
    return actor_for(
        UserResolver(engine, platform_admin_subjects=frozenset()).resolve(
            AuthenticatedIdentity(auth_subject=subject, email=f"{subject}@dev.local")
        )
    )


# -- organizations ---------------------------------------------------------


def test_only_a_platform_admin_creates_organizations(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)

    with pytest.raises(Forbidden):
        AccessService(engine, admin_a).create_organization(
            CreateOrganizationRequest(name="Acme", slug="acme")
        )

    created = AccessService(engine, ROOT).create_organization(
        CreateOrganizationRequest(name="Acme", slug="acme")
    )
    assert created.slug == "acme"
    visible = AccessService(engine, ROOT).visible_organizations()
    assert "acme" in {o.slug for o in visible}


def test_creating_an_organization_with_a_taken_slug_fails(engine: Engine) -> None:
    service = AccessService(engine, ROOT)
    service.create_organization(CreateOrganizationRequest(name="Acme", slug="acme"))

    with pytest.raises(SlugTaken):
        service.create_organization(CreateOrganizationRequest(name="Acme 2", slug="acme"))


def test_creating_an_organization_is_audited(engine: Engine) -> None:
    created = AccessService(engine, ROOT).create_organization(
        CreateOrganizationRequest(name="Acme", slug="acme")
    )

    events = AccessService(engine, ROOT).list_audit()
    assert events is not None
    event = next(e for e in events if e.action == AuditAction.ORGANIZATION_CREATED)
    assert event.actor_id == ROOT.actor_id
    assert event.target_id == created.organization_id
    assert event.details == {"name": "Acme", "slug": "acme"}


# -- memberships -----------------------------------------------------------


def test_an_organization_admin_manages_members_by_email(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)
    newcomer = _signed_in(engine, "newcomer")
    service = AccessService(engine, admin_a)

    added = service.set_member(
        "org_a", SetMemberRequest(email="newcomer@dev.local", role=OrganizationRole.VIEWER)
    )
    assert added is not None and added.role == OrganizationRole.VIEWER

    promoted = service.set_member(
        "org_a", SetMemberRequest(email="NEWCOMER@dev.local", role=OrganizationRole.EDITOR)
    )
    assert promoted is not None and promoted.role == OrganizationRole.EDITOR
    members = service.list_members("org_a")
    assert members is not None
    assert {(m.email, m.role) for m in members} == {
        ("admin-a@dev.local", OrganizationRole.ORGANIZATION_ADMIN),
        ("newcomer@dev.local", OrganizationRole.EDITOR),
    }

    assert service.remove_member("org_a", newcomer.actor_id) is True
    assert service.remove_member("org_a", newcomer.actor_id) is False
    assert MembershipRepository(engine).get(newcomer.actor_id, "org_a") is None


def test_membership_changes_are_audited_with_before_and_after(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)
    newcomer = _signed_in(engine, "newcomer")
    service = AccessService(engine, admin_a)
    service.set_member(
        "org_a", SetMemberRequest(email="newcomer@dev.local", role=OrganizationRole.VIEWER)
    )
    service.set_member(
        "org_a", SetMemberRequest(email="newcomer@dev.local", role=OrganizationRole.EDITOR)
    )
    service.remove_member("org_a", newcomer.actor_id)

    trail = service.list_audit("org_a")
    assert trail is not None
    assert [(e.action, e.details.get("previous_role"), e.details.get("role")) for e in trail] == [
        (AuditAction.MEMBERSHIP_REMOVED, "EDITOR", None),
        (AuditAction.MEMBERSHIP_SET, "VIEWER", "EDITOR"),
        (AuditAction.MEMBERSHIP_SET, None, "VIEWER"),
    ]
    assert all(e.actor_id == admin_a.actor_id for e in trail)


def test_adding_a_member_who_never_signed_in_fails(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)

    with pytest.raises(UnknownUser):
        AccessService(engine, admin_a).set_member(
            "org_a", SetMemberRequest(email="ghost@dev.local", role=OrganizationRole.VIEWER)
        )


def test_adding_by_an_email_shared_by_two_identities_is_rejected(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)
    resolver = UserResolver(engine, platform_admin_subjects=frozenset())
    resolver.resolve(AuthenticatedIdentity(auth_subject="google|1", email="same@dev.local"))
    resolver.resolve(AuthenticatedIdentity(auth_subject="auth0|2", email="same@dev.local"))

    with pytest.raises(AmbiguousEmail):
        AccessService(engine, admin_a).set_member(
            "org_a", SetMemberRequest(email="same@dev.local", role=OrganizationRole.VIEWER)
        )


def test_editors_and_viewers_cannot_manage_members(engine: Engine) -> None:
    organization(engine, "org_a")
    editor_a = member(engine, "editor-a", "org_a", OrganizationRole.EDITOR)
    _signed_in(engine, "newcomer")
    service = AccessService(engine, editor_a)

    with pytest.raises(Forbidden):
        service.list_members("org_a")
    with pytest.raises(Forbidden):
        service.set_member(
            "org_a", SetMemberRequest(email="newcomer@dev.local", role=OrganizationRole.VIEWER)
        )
    with pytest.raises(Forbidden):
        service.remove_member("org_a", editor_a.actor_id)
    with pytest.raises(Forbidden):
        service.list_audit("org_a")


def test_another_organizations_admin_sees_nothing_of_this_one(engine: Engine) -> None:
    organization(engine, "org_a")
    organization(engine, "org_b")
    member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)
    admin_b = member(engine, "admin-b", "org_b", OrganizationRole.ORGANIZATION_ADMIN)
    service = AccessService(engine, admin_b)

    assert service.list_members("org_a") is None
    assert service.list_audit("org_a") is None
    assert service.remove_member("org_a", "whoever") is False
    assert (
        service.set_member(
            "org_a", SetMemberRequest(email="admin-a@dev.local", role=OrganizationRole.VIEWER)
        )
        is None
    )
    assert service.list_members("org_missing") is None


def test_platform_admin_manages_any_organizations_members(engine: Engine) -> None:
    organization(engine, "org_a")
    _signed_in(engine, "newcomer")

    added = AccessService(engine, ROOT).set_member(
        "org_a", SetMemberRequest(email="newcomer@dev.local", role=OrganizationRole.VIEWER)
    )

    assert added is not None
    listed = AccessService(engine, ROOT).list_members("org_a")
    assert listed is not None and [m.email for m in listed] == ["newcomer@dev.local"]


# -- platform admins -------------------------------------------------------


def test_platform_admin_grants_and_revokes_platform_admin_with_audit(
    engine: Engine, root_user: ActorContext
) -> None:
    other = _signed_in(engine, "other")
    service = AccessService(engine, root_user)

    granted = service.set_platform_admin(
        other.actor_id, SetPlatformAdminRequest(is_platform_admin=True)
    )
    assert granted is not None and granted.is_platform_admin is True
    revoked = service.set_platform_admin(
        other.actor_id, SetPlatformAdminRequest(is_platform_admin=False)
    )
    assert revoked is not None and revoked.is_platform_admin is False
    # Unchanged requests are not audited twice.
    service.set_platform_admin(other.actor_id, SetPlatformAdminRequest(is_platform_admin=False))

    events = service.list_audit()
    assert events is not None
    assert [e.action for e in events if e.target_id == other.actor_id] == [
        AuditAction.PLATFORM_ADMIN_REVOKED,
        AuditAction.PLATFORM_ADMIN_GRANTED,
    ]
    assert (
        service.set_platform_admin("user_ghost", SetPlatformAdminRequest(is_platform_admin=True))
        is None
    )


def test_a_platform_admin_cannot_revoke_themselves(engine: Engine, root_user: ActorContext) -> None:
    with pytest.raises(CannotRevokeOwnPlatformAdmin):
        AccessService(engine, root_user).set_platform_admin(
            root_user.actor_id, SetPlatformAdminRequest(is_platform_admin=False)
        )
    stored = UserRepository(engine).get(root_user.actor_id)
    assert stored is not None and stored.is_platform_admin is True


def test_only_platform_admins_list_users_or_grant_platform_admin(engine: Engine) -> None:
    organization(engine, "org_a")
    admin_a = member(engine, "admin-a", "org_a", OrganizationRole.ORGANIZATION_ADMIN)
    service = AccessService(engine, admin_a)

    with pytest.raises(Forbidden):
        service.list_users()
    with pytest.raises(Forbidden):
        service.set_platform_admin(
            admin_a.actor_id, SetPlatformAdminRequest(is_platform_admin=True)
        )
    with pytest.raises(Forbidden):
        service.list_audit()


def test_list_users_shows_everyone_with_their_platform_admin_flag(engine: Engine) -> None:
    _signed_in(engine, "b-user")
    UserResolver(engine, platform_admin_subjects=frozenset({"a-admin"})).resolve(
        AuthenticatedIdentity(auth_subject="a-admin", email="a-admin@dev.local")
    )

    users = AccessService(engine, ROOT).list_users()

    assert [(u.email, u.is_platform_admin) for u in users] == [
        ("a-admin@dev.local", True),
        ("b-user@dev.local", False),
    ]


def test_bootstrap_platform_admin_grant_is_audited_as_the_system(engine: Engine) -> None:
    UserResolver(engine, platform_admin_subjects=frozenset({"first"})).resolve(
        AuthenticatedIdentity(auth_subject="first", email="first@dev.local")
    )

    events = AuditRepository(engine).list_recent()

    assert [e.action for e in events] == [AuditAction.PLATFORM_ADMIN_GRANTED]
    assert events[0].actor_id == BOOTSTRAP_ACTOR_ID
    assert events[0].details["source"] == "GREENHOUSE_PLATFORM_ADMIN_SUBJECTS"
