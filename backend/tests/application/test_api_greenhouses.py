from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

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


DAY_ONE = datetime(2026, 1, 1, tzinfo=UTC)


def _at(day: int) -> datetime:
    return DAY_ONE + timedelta(days=day - 1)


def _iso(day: int) -> str:
    return _at(day).isoformat()


def _save_state(engine: Engine, greenhouse_id: str, day: int) -> None:
    plant_state = PlantState(
        plant_id="gh_001_plant_001",
        greenhouse_id=greenhouse_id,
        timestamp=_at(day),
        health=PlantHealth.HEALTHY,
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            timestamp=_at(day),
            plant_states=[plant_state],
        )
    )


def test_get_state_without_at_returns_the_latest_snapshot(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)

    response = client.get("/greenhouses/gh_001/state")

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["timestamp"]) == _at(8)


def test_get_state_with_at_returns_the_snapshot_as_of_that_instant(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)

    response = client.get("/greenhouses/gh_001/state", params={"at": _iso(6)})

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["timestamp"]) == _at(5)


def test_get_state_returns_404_when_nothing_was_known_at_that_instant(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)

    response = client.get("/greenhouses/gh_001/state", params={"at": _iso(3)})

    assert response.status_code == 404


def test_get_timeline_lists_snapshot_instants(client: TestClient, engine: Engine) -> None:
    _save_state(engine, "gh_001", day=2)
    _save_state(engine, "gh_001", day=1)

    response = client.get("/greenhouses/gh_001/timeline")

    assert response.status_code == 200
    body = response.json()
    assert [datetime.fromisoformat(c) for c in body["checkpoints"]] == [_at(1), _at(2)]


def test_get_plant_detail_returns_plant_config_with_null_state_before_simulation_starts(
    client: TestClient,
) -> None:
    response = client.get("/greenhouses/gh_001/plants/gh_001_plant_001")

    assert response.status_code == 200
    body = response.json()
    assert body["plant"]["plant_id"] == "gh_001_plant_001"
    assert body["state"] is None


def test_get_plant_detail_includes_state_as_of_a_given_instant(
    client: TestClient, engine: Engine
) -> None:
    _save_state(engine, "gh_001", day=5)

    response = client.get("/greenhouses/gh_001/plants/gh_001_plant_001", params={"at": _iso(5)})

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["state"]["timestamp"]) == _at(5)


def test_get_plant_detail_returns_404_for_unknown_plant(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/plants/does_not_exist")

    assert response.status_code == 404


def test_get_plant_detail_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.get("/greenhouses/does_not_exist/plants/plant_001")

    assert response.status_code == 404


def test_get_plant_history_never_returns_states_after_up_to(
    client: TestClient, engine: Engine
) -> None:
    for day in range(1, 6):
        _save_state(engine, "gh_001", day)

    response = client.get(
        "/greenhouses/gh_001/plants/gh_001_plant_001/history", params={"up_to": _iso(3)}
    )

    assert response.status_code == 200
    timestamps = [datetime.fromisoformat(s["timestamp"]) for s in response.json()]
    assert timestamps == [_at(1), _at(2), _at(3)]


def test_get_plant_history_returns_404_for_unknown_plant(client: TestClient) -> None:
    response = client.get(
        "/greenhouses/gh_001/plants/does_not_exist/history", params={"up_to": _iso(5)}
    )

    assert response.status_code == 404


def test_get_timeline_is_empty_before_the_first_snapshot(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_001/timeline")

    assert response.status_code == 200
    assert response.json() == {"checkpoints": [], "current_timestamp": None}


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


def test_submit_manual_action_executes_and_returns_the_recommendation(client: TestClient) -> None:
    client.post("/simulations/sim_gh_002/next-day")

    response = client.post(
        "/greenhouses/gh_002/plants/gh_002_plant_001/actions",
        json={"action_type": "WATER_PLANT", "plant_id": "gh_002_plant_001", "amount_ml": 500},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "EXECUTED"
    assert body["source_policy"] == "NONE"
    assert body["approved_by"] == "HUMAN"
    assert body["executed_by"] == "SIMULATED_OPERATOR"


def test_submit_manual_action_rejects_mismatched_plant_id(client: TestClient) -> None:
    client.post("/simulations/sim_gh_002/next-day")

    response = client.post(
        "/greenhouses/gh_002/plants/gh_002_plant_001/actions",
        json={"action_type": "WATER_PLANT", "plant_id": "someone_else", "amount_ml": 500},
    )

    assert response.status_code == 422


def test_submit_manual_action_returns_409_before_the_simulation_has_started(
    client: TestClient,
) -> None:
    response = client.post(
        "/greenhouses/gh_002/plants/gh_002_plant_001/actions",
        json={"action_type": "WATER_PLANT", "plant_id": "gh_002_plant_001", "amount_ml": 500},
    )

    assert response.status_code == 409


def test_submit_manual_action_returns_404_for_unknown_greenhouse(client: TestClient) -> None:
    response = client.post(
        "/greenhouses/does_not_exist/plants/plant_001/actions",
        json={"action_type": "WATER_PLANT", "plant_id": "plant_001", "amount_ml": 500},
    )

    assert response.status_code == 404


def test_approve_all_recommendations_executes_every_pending_one(client: TestClient) -> None:
    client.post("/simulations/sim_gh_002/next-day")  # day 1: no recommendations for this seed
    client.post("/simulations/sim_gh_002/next-day")  # day 2: proposes a WATER_PLANT

    day_two = client.get("/greenhouses/gh_002/state").json()["timestamp"]
    response = client.post(
        "/greenhouses/gh_002/recommendations/approve-all", params={"at": day_two}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "EXECUTED"
    assert body[0]["approved_by"] == "HUMAN"

    remaining = client.get("/greenhouses/gh_002/recommendations", params={"at": day_two}).json()
    assert all(r["status"] != "PENDING" for r in remaining)


def test_approve_all_recommendations_returns_empty_list_when_nothing_pending(
    client: TestClient,
) -> None:
    response = client.post(
        "/greenhouses/gh_002/recommendations/approve-all", params={"at": _iso(1)}
    )

    assert response.status_code == 200
    assert response.json() == []
