from datetime import UTC, datetime

from sqlalchemy import Engine

from application.auth.models import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
)
from application.persistence.membership_repository import MembershipRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.user_repository import UserRepository

CREATED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _organization(organization_id: str = "org_acme", slug: str = "acme") -> Organization:
    return Organization(
        organization_id=organization_id, name="Acme Growers", slug=slug, created_at=CREATED_AT
    )


def _user(user_id: str = "user_001", auth_subject: str = "auth0|abc") -> User:
    return User(
        user_id=user_id,
        auth_subject=auth_subject,
        email="grower@acme.example",
        display_name="A. Grower",
        created_at=CREATED_AT,
    )


def test_organization_save_then_get_round_trips(engine: Engine) -> None:
    repo = OrganizationRepository(engine)
    organization = _organization()

    repo.save(organization)

    assert repo.get("org_acme") == organization
    assert repo.get_by_slug("acme") == organization
    assert repo.get("does_not_exist") is None


def test_organization_list_by_ids_returns_only_the_requested_ones(engine: Engine) -> None:
    repo = OrganizationRepository(engine)
    repo.save(_organization("org_a", "a"))
    repo.save(_organization("org_b", "b"))
    repo.save(_organization("org_c", "c"))

    listed = repo.list_by_ids(["org_a", "org_c", "org_missing"])

    assert {o.organization_id for o in listed} == {"org_a", "org_c"}
    assert repo.list_by_ids([]) == []


def test_user_save_then_get_round_trips_including_platform_admin_flag(engine: Engine) -> None:
    repo = UserRepository(engine)
    user = _user().model_copy(update={"is_platform_admin": True})

    repo.save(user)

    assert repo.get("user_001") == user
    assert repo.get_by_auth_subject("auth0|abc") == user
    assert repo.get_by_auth_subject("auth0|other") is None


def test_user_save_upserts_an_existing_user(engine: Engine) -> None:
    repo = UserRepository(engine)
    repo.save(_user())

    repo.save(_user().model_copy(update={"display_name": "Renamed"}))

    fetched = repo.get("user_001")
    assert fetched is not None
    assert fetched.display_name == "Renamed"
    assert len(repo.list()) == 1


def test_membership_round_trips_and_lists_per_user_and_per_organization(
    engine: Engine,
) -> None:
    OrganizationRepository(engine).save(_organization("org_a", "a"))
    OrganizationRepository(engine).save(_organization("org_b", "b"))
    UserRepository(engine).save(_user("user_1", "auth0|1"))
    UserRepository(engine).save(_user("user_2", "auth0|2"))
    repo = MembershipRepository(engine)
    admin_in_a = OrganizationMembership(
        user_id="user_1",
        organization_id="org_a",
        role=OrganizationRole.ORGANIZATION_ADMIN,
        created_at=CREATED_AT,
    )
    viewer_in_b = admin_in_a.model_copy(
        update={"organization_id": "org_b", "role": OrganizationRole.VIEWER}
    )
    other_in_a = admin_in_a.model_copy(
        update={"user_id": "user_2", "role": OrganizationRole.EDITOR}
    )

    repo.save(admin_in_a)
    repo.save(viewer_in_b)
    repo.save(other_in_a)

    assert repo.get("user_1", "org_a") == admin_in_a
    assert repo.get("user_1", "org_b") == viewer_in_b
    assert repo.get("user_2", "org_b") is None
    assert {m.organization_id for m in repo.list_for_user("user_1")} == {"org_a", "org_b"}
    assert {m.user_id for m in repo.list_for_organization("org_a")} == {"user_1", "user_2"}


def test_membership_save_changes_the_role_of_an_existing_membership(engine: Engine) -> None:
    OrganizationRepository(engine).save(_organization())
    UserRepository(engine).save(_user())
    repo = MembershipRepository(engine)
    membership = OrganizationMembership(
        user_id="user_001",
        organization_id="org_acme",
        role=OrganizationRole.VIEWER,
        created_at=CREATED_AT,
    )
    repo.save(membership)

    repo.save(membership.model_copy(update={"role": OrganizationRole.EDITOR}))

    fetched = repo.get("user_001", "org_acme")
    assert fetched is not None
    assert fetched.role == OrganizationRole.EDITOR
    assert len(repo.list_for_user("user_001")) == 1


def test_membership_delete_removes_only_that_membership(engine: Engine) -> None:
    OrganizationRepository(engine).save(_organization("org_a", "a"))
    OrganizationRepository(engine).save(_organization("org_b", "b"))
    UserRepository(engine).save(_user())
    repo = MembershipRepository(engine)
    for organization_id in ("org_a", "org_b"):
        repo.save(
            OrganizationMembership(
                user_id="user_001",
                organization_id=organization_id,
                role=OrganizationRole.VIEWER,
                created_at=CREATED_AT,
            )
        )

    repo.delete("user_001", "org_a")

    assert repo.get("user_001", "org_a") is None
    assert repo.get("user_001", "org_b") is not None
