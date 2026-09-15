from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.auth import AuthMode, AuthSettings, get_auth_settings, get_authenticator
from application.api.dependencies import get_engine
from application.api.main import app
from application.auth.identity import DevHeaderAuthenticator, NotAuthenticated
from application.auth.models import (
    SERRAPULSE_INTERNAL_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from application.auth.oidc import OidcAuthenticator
from application.persistence.membership_repository import MembershipRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.user_repository import UserRepository

ADMIN_SUBJECT = "dev-admin"
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_auth_settings] = lambda: AuthSettings(
        mode=AuthMode.DEV, platform_admin_subjects=frozenset({ADMIN_SUBJECT})
    )
    app.dependency_overrides[get_authenticator] = lambda: DevHeaderAuthenticator()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _as(subject: str) -> dict[str, str]:
    return {"X-Dev-Subject": subject}


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_creates_the_user_on_first_login_with_no_organizations(
    client: TestClient, engine: Engine
) -> None:
    response = client.get("/me", headers=_as("dev-alice"))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "dev-alice@dev.local"
    assert body["is_platform_admin"] is False
    assert body["organizations"] == []
    assert UserRepository(engine).get(body["user_id"]) is not None


def test_me_lists_the_organizations_the_user_belongs_to_with_their_role(
    client: TestClient, engine: Engine
) -> None:
    OrganizationRepository(engine).save(
        Organization(organization_id="org_acme", name="Acme", slug="acme", created_at=CREATED_AT)
    )
    user_id = client.get("/me", headers=_as("dev-alice")).json()["user_id"]
    MembershipRepository(engine).save(
        OrganizationMembership(
            user_id=user_id,
            organization_id="org_acme",
            role=OrganizationRole.EDITOR,
            created_at=CREATED_AT,
        )
    )

    body = client.get("/me", headers=_as("dev-alice")).json()

    assert body["organizations"] == [
        {"organization_id": "org_acme", "name": "Acme", "slug": "acme", "role": "EDITOR"}
    ]


def test_me_shows_a_platform_admin_every_organization_without_a_role(
    client: TestClient, engine: Engine
) -> None:
    OrganizationRepository(engine).save(
        Organization(organization_id="org_acme", name="Acme", slug="acme", created_at=CREATED_AT)
    )

    body = client.get("/me", headers=_as(ADMIN_SUBJECT)).json()

    assert body["is_platform_admin"] is True
    assert [o["organization_id"] for o in body["organizations"]] == [
        "org_acme",
        SERRAPULSE_INTERNAL_ORGANIZATION_ID,
    ]
    assert all(o["role"] is None for o in body["organizations"])


def test_app_refuses_to_start_without_an_auth_mode(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GREENHOUSE_AUTH_MODE")
    monkeypatch.setenv("GREENHOUSE_DATABASE_URL", str(engine.url))

    with pytest.raises(RuntimeError, match="GREENHOUSE_AUTH_MODE"), TestClient(app):
        pass


def test_app_starts_in_dev_mode_and_authenticates_the_header(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GREENHOUSE_DATABASE_URL", engine.url.render_as_string(hide_password=False))

    with TestClient(app) as started:
        assert started.get("/me").status_code == 401
        assert started.get("/me", headers=_as("dev-bob")).status_code == 200


def test_oidc_mode_requires_issuer_and_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GREENHOUSE_AUTH_MODE", "oidc")
    monkeypatch.delenv("GREENHOUSE_OIDC_ISSUER", raising=False)
    monkeypatch.setenv("GREENHOUSE_OIDC_AUDIENCE", "https://api")

    with pytest.raises(RuntimeError, match="GREENHOUSE_OIDC_ISSUER"):
        AuthSettings.from_env()

    monkeypatch.setenv("GREENHOUSE_OIDC_ISSUER", "http://insecure.example/")
    with pytest.raises(RuntimeError, match="https://"):
        AuthSettings.from_env()


def test_oidc_mode_builds_a_bearer_token_authenticator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GREENHOUSE_AUTH_MODE", "oidc")
    monkeypatch.setenv("GREENHOUSE_OIDC_ISSUER", "https://tenant.eu.auth0.com/")
    monkeypatch.setenv("GREENHOUSE_OIDC_AUDIENCE", "https://api.serrapulse.example")
    monkeypatch.setenv("GREENHOUSE_OIDC_EMAIL_CLAIM", "https://serrapulse/email")

    settings = AuthSettings.from_env()

    assert settings.mode == AuthMode.OIDC
    assert settings.oidc is not None
    assert settings.oidc.jwks_url == "https://tenant.eu.auth0.com/.well-known/jwks.json"
    assert settings.oidc.email_claim == "https://serrapulse/email"
    assert isinstance(settings.authenticator(), OidcAuthenticator)
    # Without a token, an X-Dev-Subject header means nothing in this mode.
    with pytest.raises(NotAuthenticated):
        settings.authenticator().authenticate({"x-dev-subject": "dev-admin"})
