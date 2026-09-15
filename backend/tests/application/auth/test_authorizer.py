from datetime import UTC, datetime

import pytest

from application.auth.actor import ActorContext
from application.auth.authorizer import Action, Authorizer, Forbidden, role_permits
from application.auth.models import OrganizationMembership, OrganizationRole

CREATED_AT = datetime(2026, 9, 1, tzinfo=UTC)


class FakeMemberships:
    def __init__(self, *memberships: tuple[str, str, OrganizationRole]) -> None:
        self._rows = [
            OrganizationMembership(
                user_id=user_id, organization_id=organization_id, role=role, created_at=CREATED_AT
            )
            for user_id, organization_id, role in memberships
        ]

    def get(self, user_id: str, organization_id: str) -> OrganizationMembership | None:
        return next(
            (m for m in self._rows if (m.user_id, m.organization_id) == (user_id, organization_id)),
            None,
        )

    def list_for_user(self, user_id: str) -> list[OrganizationMembership]:
        return [m for m in self._rows if m.user_id == user_id]


VIEWER = ActorContext.user("u_viewer")
EDITOR = ActorContext.user("u_editor")
ORG_ADMIN = ActorContext.user("u_admin")
OUTSIDER = ActorContext.user("u_outsider")
PLATFORM_ADMIN = ActorContext.user("u_root", is_platform_admin=True)


@pytest.fixture
def authorizer() -> Authorizer:
    return Authorizer(
        FakeMemberships(
            ("u_viewer", "org_a", OrganizationRole.VIEWER),
            ("u_editor", "org_a", OrganizationRole.EDITOR),
            ("u_admin", "org_a", OrganizationRole.ORGANIZATION_ADMIN),
            ("u_admin", "org_b", OrganizationRole.VIEWER),
            ("u_outsider", "org_b", OrganizationRole.ORGANIZATION_ADMIN),
        )
    )


@pytest.mark.parametrize(
    ("actor", "action", "allowed"),
    [
        (VIEWER, Action.GREENHOUSE_READ, True),
        (VIEWER, Action.ORGANIZATION_READ, True),
        (VIEWER, Action.GREENHOUSE_WRITE, False),
        (VIEWER, Action.MEMBERSHIP_MANAGE, False),
        (EDITOR, Action.GREENHOUSE_READ, True),
        (EDITOR, Action.GREENHOUSE_WRITE, True),
        (EDITOR, Action.MEMBERSHIP_MANAGE, False),
        (ORG_ADMIN, Action.GREENHOUSE_WRITE, True),
        (ORG_ADMIN, Action.MEMBERSHIP_MANAGE, True),
        (ORG_ADMIN, Action.GREENHOUSE_CREATE, False),
        (ORG_ADMIN, Action.GREENHOUSE_DELETE, False),
        (ORG_ADMIN, Action.PLATFORM_ADMINISTER, False),
        (PLATFORM_ADMIN, Action.GREENHOUSE_CREATE, True),
        (PLATFORM_ADMIN, Action.MEMBERSHIP_MANAGE, True),
        (PLATFORM_ADMIN, Action.PLATFORM_ADMINISTER, True),
    ],
)
def test_role_table_inside_org_a(
    authorizer: Authorizer, actor: ActorContext, action: Action, allowed: bool
) -> None:
    assert authorizer.can(actor, action, "org_a") is allowed


def test_membership_in_another_organization_grants_nothing_here(authorizer: Authorizer) -> None:
    # An admin of org_b guessing org_a identifiers gets nowhere.
    assert not authorizer.can(OUTSIDER, Action.GREENHOUSE_READ, "org_a")
    assert not authorizer.can(OUTSIDER, Action.MEMBERSHIP_MANAGE, "org_a")


def test_the_same_user_has_a_different_role_per_organization(authorizer: Authorizer) -> None:
    assert authorizer.can(ORG_ADMIN, Action.MEMBERSHIP_MANAGE, "org_a")
    assert authorizer.can(ORG_ADMIN, Action.GREENHOUSE_READ, "org_b")
    assert not authorizer.can(ORG_ADMIN, Action.GREENHOUSE_WRITE, "org_b")


def test_platform_wide_actions_need_a_platform_admin(authorizer: Authorizer) -> None:
    assert authorizer.can(PLATFORM_ADMIN, Action.PLATFORM_ADMINISTER, None)
    assert not authorizer.can(ORG_ADMIN, Action.PLATFORM_ADMINISTER, None)
    assert not authorizer.can(ORG_ADMIN, Action.GREENHOUSE_READ, None)


def test_require_raises_forbidden_naming_actor_action_and_organization(
    authorizer: Authorizer,
) -> None:
    with pytest.raises(Forbidden) as info:
        authorizer.require(VIEWER, Action.GREENHOUSE_WRITE, "org_a")

    assert info.value.actor == VIEWER
    assert info.value.action == Action.GREENHOUSE_WRITE
    assert info.value.organization_id == "org_a"
    assert "u_viewer" in str(info.value) and "org_a" in str(info.value)


def test_require_passes_silently_when_allowed(authorizer: Authorizer) -> None:
    authorizer.require(EDITOR, Action.GREENHOUSE_WRITE, "org_a")


def test_visible_organizations_are_the_memberships_or_unrestricted_for_platform_admin(
    authorizer: Authorizer,
) -> None:
    assert authorizer.visible_organization_ids(ORG_ADMIN) == ["org_a", "org_b"]
    assert authorizer.visible_organization_ids(ActorContext.user("u_nobody")) == []
    assert authorizer.visible_organization_ids(PLATFORM_ADMIN) is None


def test_role_in_reports_the_membership_role_or_none(authorizer: Authorizer) -> None:
    assert authorizer.role_in(ORG_ADMIN, "org_b") == OrganizationRole.VIEWER
    assert authorizer.role_in(ORG_ADMIN, "org_zzz") is None


def test_every_action_has_a_rule() -> None:
    for action in Action:
        # Either some role permits it or it is platform-admin only; the
        # table must not silently miss a new Action member.
        role_permits(OrganizationRole.ORGANIZATION_ADMIN, action)
