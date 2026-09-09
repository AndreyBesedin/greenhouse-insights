"""The one sanctioned end-to-end test for Milestone 1 (DEVELOPMENT_GUIDELINES.md).

Walks the full backbone flow through the real HTTP API and a real (temp)
SQLite database: list greenhouses -> open GH002 -> run its simulation to
completion -> navigate to a past day -> return to the current day -> switch
to GH001 and run it too, proving the same architecture serves a completely
different greenhouse size/duration without any greenhouse-specific code.
"""

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine, get_simulation_service
from application.api.main import app
from application.bootstrap import bootstrap_greenhouses
from application.simulation_service import SimulationService


@pytest.fixture
def client(engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    bootstrap_greenhouses(engine)
    monkeypatch.setenv("GREENHOUSE_DATABASE_URL", f"sqlite:///{tmp_path / 'unused.db'}")
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_simulation_service] = lambda: SimulationService(
        engine, step_delay_seconds=0
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _run_to_completion(client: TestClient, simulation_id: str, *, total_steps: int) -> None:
    client.post(f"/simulations/{simulation_id}/run")
    for _ in range(200):
        status = client.get(f"/simulations/{simulation_id}/status").json()
        if status["status"] == "COMPLETED":
            assert status["current_step"] == total_steps
            return
        time.sleep(0.02)
    pytest.fail(f"{simulation_id} did not complete in time")


def test_backbone_flow_across_configured_greenhouses(client: TestClient) -> None:
    # 1. Greenhouse selection screen lists every configured greenhouse, NOT_STARTED.
    listed = client.get("/greenhouses").json()
    assert {item["greenhouse_id"] for item in listed} == {"gh_001", "gh_002", "gh_demo"}
    assert all(item["status"] == "NOT_STARTED" for item in listed)

    # 2. Open GH002 (the small, config-driven demo greenhouse) at Day 0.
    gh_002_detail = client.get("/greenhouses/gh_002").json()
    assert len(gh_002_detail["greenhouse"]["plants"]) == 1
    assert gh_002_detail["simulation"]["current_step"] == 0
    assert gh_002_detail["simulation"]["total_steps"] == 40

    # 3-4. Run it and watch it progress to completion.
    _run_to_completion(client, "sim_gh_002", total_steps=40)

    # 5. Current state is Day 40/40, persisted.
    current_state = client.get("/greenhouses/gh_002/state").json()
    assert current_state["simulated_day"] == 40

    # 6. Navigate backwards to a historical day...
    past_state = client.get("/greenhouses/gh_002/state?day=20").json()
    assert past_state["simulated_day"] == 20

    plant_id = gh_002_detail["greenhouse"]["plants"][0]["plant_id"]
    history = client.get(f"/greenhouses/gh_002/plants/{plant_id}/history?up_to_day=20").json()
    assert [entry["simulated_day"] for entry in history] == list(range(1, 21))

    # 7. ...then return to the current (final) day.
    returned_state = client.get("/greenhouses/gh_002/state").json()
    assert returned_state["simulated_day"] == 40

    # 8. Back to the greenhouse list, open the primary 40-plant/28-day greenhouse.
    gh_001_detail = client.get("/greenhouses/gh_001").json()
    assert len(gh_001_detail["greenhouse"]["plants"]) == 40
    assert gh_001_detail["simulation"]["total_steps"] == 28
    assert gh_001_detail["simulation"]["status"] == "NOT_STARTED"

    # 9. Run GH001 too: same runner, service, and endpoints, different shape.
    _run_to_completion(client, "sim_gh_001", total_steps=28)

    gh_001_state = client.get("/greenhouses/gh_001/state").json()
    assert gh_001_state["simulated_day"] == 28
    assert len(gh_001_state["plant_states"]) == 40

    # GH002 remains independently completed and untouched by GH001's run.
    assert client.get("/simulations/sim_gh_002/status").json()["status"] == "COMPLETED"
