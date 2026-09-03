from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.api.main import app
from application.bootstrap import bootstrap_greenhouses


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    bootstrap_greenhouses(engine)
    app.dependency_overrides[get_engine] = lambda: engine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_agent_provider_reports_fake_by_default(client: TestClient) -> None:
    response = client.get("/system/agent-provider")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAKE"
    assert body["provider"] == "fake"
    assert body["model"] is None


def test_agent_provider_reports_configured_when_anthropic_is_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")

    response = client.get("/system/agent-provider")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONFIGURED"
    assert body["model"] == "claude-sonnet-5"


def test_agent_provider_reports_misconfigured_without_an_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.get("/system/agent-provider")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MISCONFIGURED"
    assert body["detail"] is not None
