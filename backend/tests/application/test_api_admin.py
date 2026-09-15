from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.api.main import app
from application.auth.models import OrganizationRole
from tests.application.support import (
    ADMIN_HEADERS,
    as_user,
    greenhouse,
    install_dev_auth,
    member,
    organization,
)


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    app.dependency_overrides[get_engine] = lambda: engine
    install_dev_auth()
    yield TestClient(app, headers=ADMIN_HEADERS)
    app.dependency_overrides.clear()


def test_admin_routes_require_authentication(client: TestClient) -> None:
    anonymous = TestClient(app)

    assert anonymous.get("/organizations").status_code == 401
    assert anonymous.post("/organizations", json={"name": "x", "slug": "x"}).status_code == 401
    assert anonymous.get("/admin/users").status_code == 401
    assert anonymous.get("/admin/audit").status_code == 401


def test_platform_admin_creates_an_organization_and_sees_it_listed(client: TestClient) -> None:
    created = client.post("/organizations", json={"name": "Acme Growers", "slug": "acme"})

    assert created.status_code == 201
    assert created.json()["slug"] == "acme"
    assert client.post("/organizations", json={"name": "Dup", "slug": "acme"}).status_code == 409
    assert (
        client.post("/organizations", json={"name": "Bad", "slug": "Not Slug"}).status_code == 422
    )
    listed = client.get("/organizations").json()
    assert "acme" in {o["slug"] for o in listed}


def test_an_organization_admin_administers_members_over_http(
    client: TestClient, engine: Engine
) -> None:
    organization(engine, "org_acme")
    member(engine, "acme-admin", "org_acme", OrganizationRole.ORGANIZATION_ADMIN)
    client.get("/me", headers=as_user("acme-newcomer"))  # signs in once
    admin = as_user("acme-admin")

    added = client.put(
        "/organizations/org_acme/members",
        json={"email": "acme-newcomer@dev.local", "role": "EDITOR"},
        headers=admin,
    )
    assert added.status_code == 200
    assert added.json()["role"] == "EDITOR"
    members = client.get("/organizations/org_acme/members", headers=admin).json()
    assert {m["email"] for m in members} == {"acme-admin@dev.local", "acme-newcomer@dev.local"}

    removed = client.delete(
        f"/organizations/org_acme/members/{added.json()['user_id']}", headers=admin
    )
    assert removed.status_code == 204
    assert (
        client.delete(
            f"/organizations/org_acme/members/{added.json()['user_id']}", headers=admin
        ).status_code
        == 404
    )
    audit = client.get("/organizations/org_acme/audit", headers=admin).json()
    assert [e["action"] for e in audit] == ["MEMBERSHIP_REMOVED", "MEMBERSHIP_SET"]


def test_member_administration_status_codes(client: TestClient, engine: Engine) -> None:
    organization(engine, "org_acme")
    organization(engine, "org_other")
    member(engine, "acme-admin", "org_acme", OrganizationRole.ORGANIZATION_ADMIN)
    member(engine, "acme-editor", "org_acme", OrganizationRole.EDITOR)
    admin, editor = as_user("acme-admin"), as_user("acme-editor")

    unknown = client.put(
        "/organizations/org_acme/members",
        json={"email": "ghost@dev.local", "role": "VIEWER"},
        headers=admin,
    )
    assert unknown.status_code == 404
    assert client.get("/organizations/org_acme/members", headers=editor).status_code == 403
    assert client.get("/organizations/org_other/members", headers=admin).status_code == 404
    assert client.get("/organizations/org_acme/audit", headers=editor).status_code == 403


def test_platform_admin_user_administration_over_http(client: TestClient) -> None:
    me = client.get("/me").json()
    other = client.get("/me", headers=as_user("someone")).json()

    users = client.get("/admin/users").json()
    assert {u["email"] for u in users} == {"dev-admin@dev.local", "someone@dev.local"}

    granted = client.put(
        f"/admin/users/{other['user_id']}/platform-admin", json={"is_platform_admin": True}
    )
    assert granted.status_code == 200 and granted.json()["is_platform_admin"] is True
    assert client.get("/me", headers=as_user("someone")).json()["is_platform_admin"] is True

    self_revoke = client.put(
        f"/admin/users/{me['user_id']}/platform-admin", json={"is_platform_admin": False}
    )
    assert self_revoke.status_code == 409
    assert (
        client.put(
            "/admin/users/user_ghost/platform-admin", json={"is_platform_admin": True}
        ).status_code
        == 404
    )
    assert client.get("/admin/users", headers=as_user("nobody")).status_code == 403

    actions = [e["action"] for e in client.get("/admin/audit").json()]
    assert "PLATFORM_ADMIN_GRANTED" in actions


def test_platform_admin_reassigns_a_greenhouse_over_http(
    client: TestClient, engine: Engine
) -> None:
    organization(engine, "org_acme")
    greenhouse(engine, "gh_x", "org_acme")
    member(engine, "acme-admin", "org_acme", OrganizationRole.ORGANIZATION_ADMIN)

    forbidden = client.put(
        "/greenhouses/gh_x/organization",
        json={"organization_id": "org_serrapulse_internal"},
        headers=as_user("acme-admin"),
    )
    assert forbidden.status_code == 403
    bad_target = client.put("/greenhouses/gh_x/organization", json={"organization_id": "nope"})
    assert bad_target.status_code == 422
    moved = client.put(
        "/greenhouses/gh_x/organization", json={"organization_id": "org_serrapulse_internal"}
    )
    assert moved.status_code == 200
    assert moved.json()["greenhouse"]["organization_id"] == "org_serrapulse_internal"
    assert client.get("/greenhouses/gh_x", headers=as_user("acme-admin")).status_code == 404
