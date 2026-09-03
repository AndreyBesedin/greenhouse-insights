from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine, get_simulation_service
from application.api.main import app
from application.bootstrap import bootstrap_greenhouses
from application.persistence.state_repository import StateRepository
from application.simulation_service import SimulationService
from domain.enums import PlantHealth
from domain.state import GreenhouseState, PlantState


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    bootstrap_greenhouses(engine)
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_simulation_service] = lambda: SimulationService(
        engine, step_delay_seconds=0
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_greenhouses_returns_all_seeded_greenhouses(client: TestClient) -> None:
    response = client.get("/greenhouses")

    assert response.status_code == 200
    body = response.json()
    assert {item["greenhouse_id"] for item in body} == {"gh_001", "gh_002", "gh_demo"}
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


def test_get_plant_history_never_returns_days_beyond_up_to_day(
    client: TestClient, engine: Engine
) -> None:
    for day in range(1, 6):
        _save_state(engine, "gh_001", day)

    response = client.get("/greenhouses/gh_001/plants/gh_001_plant_001/history?up_to_day=3")

    assert response.status_code == 200
    days = [s["simulated_day"] for s in response.json()]
    assert days == [1, 2, 3]


def test_get_plant_history_returns_404_for_unknown_plant(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/plants/does_not_exist/history?up_to_day=5")

    assert response.status_code == 404


def test_get_timeline_reports_total_and_current_day(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["total_days"] == 28
    assert body["current_day"] == 0


def test_get_timeline_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.get("/greenhouses/does_not_exist/timeline")

    assert response.status_code == 404


def test_create_greenhouse_with_simulation_source_returns_a_runnable_greenhouse(
    client: TestClient,
) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "New Greenhouse",
            "source_type": "SIMULATION",
            "crop": "cherry_tomato",
            "rows": 2,
            "columns": 3,
            "duration_days": 10,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["greenhouse"]["plants"]) == 6
    assert body["simulation"]["status"] == "NOT_STARTED"
    assert body["simulation"]["total_steps"] == 10

    greenhouse_id = body["greenhouse"]["greenhouse_id"]
    get_response = client.get(f"/greenhouses/{greenhouse_id}")
    assert get_response.status_code == 200
    assert get_response.json()["simulation"]["simulation_id"] == f"sim_{greenhouse_id}"


def test_create_greenhouse_with_real_sensors_source_has_null_simulation(
    client: TestClient,
) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "Live Greenhouse",
            "source_type": "REAL_SENSORS",
            "crop": "cherry_tomato",
            "rows": 1,
            "columns": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["simulation"] is None


def test_create_greenhouse_without_duration_days_is_rejected_for_simulation_source(
    client: TestClient,
) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "New Greenhouse",
            "source_type": "SIMULATION",
            "crop": "cherry_tomato",
            "rows": 1,
            "columns": 1,
        },
    )

    assert response.status_code == 422


def test_create_greenhouse_rejects_an_oversized_grid(client: TestClient) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "New Greenhouse",
            "source_type": "SIMULATION",
            "crop": "cherry_tomato",
            "rows": 1000,
            "columns": 1,
            "duration_days": 10,
        },
    )

    assert response.status_code == 422


def test_create_greenhouse_rejects_an_overlong_agentic_duration(client: TestClient) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "New Greenhouse",
            "source_type": "SIMULATION",
            "crop": "cherry_tomato",
            "rows": 1,
            "columns": 1,
            "duration_days": 31,
            "management_policy": "AGENTIC",
        },
    )

    assert response.status_code == 422


def test_create_greenhouse_rejects_too_many_plants_for_agentic(client: TestClient) -> None:
    response = client.post(
        "/greenhouses",
        json={
            "name": "New Greenhouse",
            "source_type": "SIMULATION",
            "crop": "cherry_tomato",
            "rows": 5,
            "columns": 6,
            "duration_days": 10,
            "management_policy": "AGENTIC",
        },
    )

    assert response.status_code == 422


def test_delete_greenhouse_removes_it_and_returns_204(client: TestClient) -> None:
    response = client.delete("/greenhouses/gh_001")

    assert response.status_code == 204
    assert client.get("/greenhouses/gh_001").status_code == 404
    remaining = {item["greenhouse_id"] for item in client.get("/greenhouses").json()}
    assert remaining == {"gh_002", "gh_demo"}


def test_delete_greenhouse_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.delete("/greenhouses/does_not_exist")

    assert response.status_code == 404


def test_delete_greenhouse_cancels_a_running_simulation(client: TestClient) -> None:
    run_response = client.post("/simulations/sim_gh_001/run")
    assert run_response.status_code == 200

    delete_response = client.delete("/greenhouses/gh_001")

    assert delete_response.status_code == 204
    assert client.get("/greenhouses/gh_001").status_code == 404
