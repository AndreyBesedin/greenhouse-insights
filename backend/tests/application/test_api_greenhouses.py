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


def test_list_greenhouses_returns_both_seeded_greenhouses(client: TestClient) -> None:
    response = client.get("/greenhouses")

    assert response.status_code == 200
    body = response.json()
    assert {item["greenhouse_id"] for item in body} == {"gh_001", "gh_002"}
    assert all(item["status"] == "NOT_STARTED" for item in body)


def test_get_greenhouse_detail_returns_full_greenhouse_and_simulation(
    client: TestClient,
) -> None:
    response = client.get("/greenhouses/gh_001")

    assert response.status_code == 200
    body = response.json()
    assert len(body["greenhouse"]["plants"]) == 40
    assert body["simulation"]["status"] == "NOT_STARTED"
    assert body["simulation"]["total_steps"] == 28


def test_get_greenhouse_detail_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.get("/greenhouses/does_not_exist")

    assert response.status_code == 404
