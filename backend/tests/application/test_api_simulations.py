import time
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
    ScenarioConfigRepository(engine).save(SCENARIO_REGISTRY["gh_002"])
    SimulationRepository(engine).save(
        SimulationDefinition(
            simulation_id="sim_test",
            greenhouse_id="gh_test",
            scenario_definition="gh_002",
            start_date=date(2026, 1, 1),
            duration_days=2,
            random_seed=42,
            total_steps=2,
        )
    )


@pytest.fixture
def client(engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    _seed(engine)
    # lifespan() builds its own (unused) engine from this env var; point it at a
    # throwaway path so it never touches the real backend/data directory. Actual
    # requests use the engine/service overridden below instead.
    monkeypatch.setenv("GREENHOUSE_DATABASE_URL", f"sqlite:///{tmp_path / 'unused.db'}")
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_simulation_service] = lambda: SimulationService(
        engine, step_delay_seconds=0
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_status_before_running_reports_not_started(client: TestClient) -> None:
    response = client.get("/simulations/sim_test/status")

    assert response.status_code == 200
    assert response.json()["status"] == "NOT_STARTED"
    assert response.json()["current_step"] == 0


def test_run_then_poll_status_walks_to_completed(client: TestClient) -> None:
    run_response = client.post("/simulations/sim_test/run")
    assert run_response.status_code == 200

    status = None
    for _ in range(50):
        status = client.get("/simulations/sim_test/status").json()
        if status["status"] == "COMPLETED":
            break
        time.sleep(0.05)

    assert status is not None
    assert status["status"] == "COMPLETED"
    assert status["current_step"] == 2


def test_run_returns_404_for_unknown_simulation(client: TestClient) -> None:
    response = client.post("/simulations/does_not_exist/run")

    assert response.status_code == 404


def test_get_status_returns_404_for_unknown_simulation(client: TestClient) -> None:
    response = client.get("/simulations/does_not_exist/status")

    assert response.status_code == 404


def test_next_day_advances_exactly_one_step(client: TestClient) -> None:
    response = client.post("/simulations/sim_test/next-day")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RUNNING"
    assert body["current_step"] == 1


def test_next_day_called_repeatedly_stops_at_each_day(client: TestClient) -> None:
    first = client.post("/simulations/sim_test/next-day").json()
    second = client.post("/simulations/sim_test/next-day").json()

    assert first["current_step"] == 1
    assert second["current_step"] == 2
    assert second["status"] == "COMPLETED"


def test_next_day_returns_404_for_unknown_simulation(client: TestClient) -> None:
    response = client.post("/simulations/does_not_exist/next-day")

    assert response.status_code == 404
