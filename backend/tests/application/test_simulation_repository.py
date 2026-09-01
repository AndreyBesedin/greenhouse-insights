from datetime import date
from pathlib import Path

from sqlalchemy import Engine

from application.db import create_engine_and_tables
from application.persistence.simulation_repository import SimulationRepository
from domain.enums import SimulationStatus
from simulation.definitions import SimulationDefinition


def _make_definition(**overrides: object) -> SimulationDefinition:
    defaults: dict[str, object] = dict(
        simulation_id="sim_gh_001",
        greenhouse_id="gh_001",
        scenario_definition="gh_001",
        start_date=date(2026, 1, 1),
        duration_days=28,
        random_seed=1001,
        total_steps=28,
    )
    defaults.update(overrides)
    return SimulationDefinition(**defaults)


def test_save_then_get_round_trips_the_definition(engine: Engine) -> None:
    repo = SimulationRepository(engine)
    definition = _make_definition()

    repo.save(definition)

    assert repo.get(definition.simulation_id) == definition


def test_get_returns_none_for_unknown_simulation(engine: Engine) -> None:
    repo = SimulationRepository(engine)

    assert repo.get("does_not_exist") is None


def test_delete_removes_the_definition(engine: Engine) -> None:
    repo = SimulationRepository(engine)
    definition = _make_definition()
    repo.save(definition)

    repo.delete(definition.simulation_id)

    assert repo.get(definition.simulation_id) is None


def test_delete_is_a_noop_for_an_unknown_simulation(engine: Engine) -> None:
    repo = SimulationRepository(engine)

    repo.delete("does_not_exist")  # should not raise


def test_status_and_current_step_survive_reopening_a_fresh_engine(db_path: Path) -> None:
    first_engine = create_engine_and_tables(f"sqlite:///{db_path}")
    definition = _make_definition()
    SimulationRepository(first_engine).save(definition)

    progressed = definition.model_copy(
        update={"current_step": 11, "status": SimulationStatus.RUNNING}
    )
    SimulationRepository(first_engine).save(progressed)
    first_engine.dispose()

    second_engine = create_engine_and_tables(f"sqlite:///{db_path}")
    reloaded = SimulationRepository(second_engine).get(definition.simulation_id)

    assert reloaded is not None
    assert reloaded.current_step == 11
    assert reloaded.status == SimulationStatus.RUNNING
