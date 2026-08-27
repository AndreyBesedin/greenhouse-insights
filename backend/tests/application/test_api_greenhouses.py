from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.api.main import app
from application.bootstrap import bootstrap_greenhouses
from application.persistence.state_repository import StateRepository
from domain.enums import PlantHealth
from domain.state import GreenhouseState, PlantState


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


def _save_state(engine: Engine, greenhouse_id: str, day: int) -> None:
    plant_state = PlantState(
        plant_id="gh_001_plant_001",
        greenhouse_id=greenhouse_id,
        simulated_day=day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        health=PlantHealth.HEALTHY,
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            simulated_day=day,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            plant_states=[plant_state],
        )
    )


def test_get_state_without_day_returns_the_latest_snapshot(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)

    response = client.get("/greenhouses/gh_001/state")

    assert response.status_code == 200
    assert response.json()["simulated_day"] == 8


def test_get_state_with_day_returns_that_specific_snapshot(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)

    response = client.get("/greenhouses/gh_001/state?day=5")

    assert response.status_code == 200
    assert response.json()["simulated_day"] == 5


def test_get_state_returns_404_when_day_has_no_snapshot(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/state?day=3")

    assert response.status_code == 404


def test_get_plant_detail_returns_plant_config_with_null_state_before_simulation_starts(
    client: TestClient,
) -> None:
    response = client.get("/greenhouses/gh_001/plants/gh_001_plant_001")

    assert response.status_code == 200
    body = response.json()
    assert body["plant"]["plant_id"] == "gh_001_plant_001"
    assert body["state"] is None


def test_get_plant_detail_includes_state_for_a_given_day(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)

    response = client.get("/greenhouses/gh_001/plants/gh_001_plant_001?day=5")

    assert response.status_code == 200
    assert response.json()["state"]["simulated_day"] == 5


def test_get_plant_detail_returns_404_for_unknown_plant(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/plants/does_not_exist")

    assert response.status_code == 404


def test_get_plant_detail_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.get("/greenhouses/does_not_exist/plants/plant_001")

    assert response.status_code == 404
