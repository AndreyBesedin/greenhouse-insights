from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine, get_simulation_service
from application.api.main import app
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.simulation_service import SimulationService
from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from simulation.definitions import SimulationDefinition
from simulation.scenarios import SCENARIO_REGISTRY


def _seed(engine: Engine) -> None:
    greenhouse = Greenhouse(
        greenhouse_id="gh_test",
        name="Test Greenhouse",
        description="A test greenhouse",
        source_type=SourceType.SIMULATION,
        layout=GreenhouseLayout(rows=1, columns=1),
        plants=[
            Plant(plant_id="gh_test_plant_001", variety="cherry_tomato", row=1, position_in_row=1)
        ],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    GreenhouseRepository(engine).save(greenhouse)
    # For this seed, gh_002's moisture crosses the watering trigger on day 2
    # (day 1 does not yet), reliably producing exactly one WATER_PLANT
    # recommendation there - a real, non-fabricated signal to review rather
    # than a hand-built fixture.
    ScenarioConfigRepository(engine).save(SCENARIO_REGISTRY["gh_002"])
    SimulationRepository(engine).save(
        SimulationDefinition(
            simulation_id="sim_test",
            greenhouse_id="gh_test",
            scenario_definition="gh_002",
            start_date=date(2026, 1, 1),
            duration_days=3,
            random_seed=42,
            total_steps=3,
        )
    )


@pytest.fixture
def client(engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    _seed(engine)
    monkeypatch.setenv("GREENHOUSE_DATABASE_URL", f"sqlite:///{tmp_path / 'unused.db'}")
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_simulation_service] = lambda: SimulationService(
        engine, step_delay_seconds=0
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _advance_to_a_pending_recommendation(client: TestClient) -> str:
    client.post("/simulations/sim_test/next-day")  # day 1: nothing proposed for this seed
    client.post("/simulations/sim_test/next-day")  # day 2: proposes a WATER_PLANT
    recommendations = client.get("/greenhouses/gh_test/recommendations", params={"day": 2}).json()
    assert len(recommendations) >= 1
    pending = next(r for r in recommendations if r["status"] == "PENDING")
    return str(pending["recommendation_id"])


def test_get_recommendations_returns_the_proposal_from_advancing(client: TestClient) -> None:
    client.post("/simulations/sim_test/next-day")
    client.post("/simulations/sim_test/next-day")

    response = client.get("/greenhouses/gh_test/recommendations", params={"day": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["status"] == "PENDING"
    assert body[0]["source_policy"] == "DETERMINISTIC"
    assert body[0]["reason"]


def test_get_recommendations_returns_empty_for_a_day_with_none(client: TestClient) -> None:
    response = client.get("/greenhouses/gh_test/recommendations", params={"day": 1})

    assert response.status_code == 200
    assert response.json() == []


def test_approve_recommendation_executes_it(client: TestClient) -> None:
    recommendation_id = _advance_to_a_pending_recommendation(client)

    response = client.post(f"/recommendations/{recommendation_id}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXECUTED"
    assert body["approved_by"] == "HUMAN"
    assert body["executed_by"] == "SIMULATED_OPERATOR"


def test_dismiss_recommendation_marks_it_dismissed(client: TestClient) -> None:
    recommendation_id = _advance_to_a_pending_recommendation(client)

    response = client.post(f"/recommendations/{recommendation_id}/dismiss")

    assert response.status_code == 200
    assert response.json()["status"] == "DISMISSED"


def test_approving_an_already_reviewed_recommendation_returns_409(client: TestClient) -> None:
    recommendation_id = _advance_to_a_pending_recommendation(client)
    client.post(f"/recommendations/{recommendation_id}/dismiss")

    response = client.post(f"/recommendations/{recommendation_id}/approve")

    assert response.status_code == 409


def test_dismissing_an_already_reviewed_recommendation_returns_409(client: TestClient) -> None:
    recommendation_id = _advance_to_a_pending_recommendation(client)
    client.post(f"/recommendations/{recommendation_id}/approve")

    response = client.post(f"/recommendations/{recommendation_id}/dismiss")

    assert response.status_code == 409


def test_approve_returns_404_for_unknown_recommendation(client: TestClient) -> None:
    response = client.post("/recommendations/does_not_exist/approve")

    assert response.status_code == 404


def test_dismiss_returns_404_for_unknown_recommendation(client: TestClient) -> None:
    response = client.post("/recommendations/does_not_exist/dismiss")

    assert response.status_code == 404


def test_full_review_cycle_then_advancing_reaches_the_next_day(client: TestClient) -> None:
    recommendation_id = _advance_to_a_pending_recommendation(client)

    client.post(f"/recommendations/{recommendation_id}/approve")
    next_day = client.post("/simulations/sim_test/next-day")

    assert next_day.status_code == 200
    assert next_day.json()["current_step"] == 3
