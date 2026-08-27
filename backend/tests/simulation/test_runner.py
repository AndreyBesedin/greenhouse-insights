import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from domain.enums import SimulationStatus, SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from simulation.definitions import SimulationDefinition
from simulation.runner import SimulationRunner


def _seed_greenhouse_and_simulation(
    engine: Engine, *, current_step: int = 0, total_steps: int = 3
) -> None:
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

    definition = SimulationDefinition(
        simulation_id="sim_test",
        greenhouse_id="gh_test",
        scenario_definition="gh_002",
        start_date=date(2026, 1, 1),
        duration_days=total_steps,
        random_seed=42,
        current_step=current_step,
        status=SimulationStatus.RUNNING if current_step > 0 else SimulationStatus.NOT_STARTED,
        total_steps=total_steps,
    )
    SimulationRepository(engine).save(definition)


def test_run_to_completion_persists_every_day_and_marks_completed(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(engine, total_steps=3)
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion("sim_test"))

    definition = SimulationRepository(engine).get("sim_test")
    assert definition is not None
    assert definition.status == SimulationStatus.COMPLETED
    assert definition.current_step == 3

    state_repo = StateRepository(engine)
    for day in (1, 2, 3):
        assert state_repo.get("gh_test", day=day) is not None

    observations = ObservationRepository(engine).list_for_greenhouse("gh_test")
    assert {obs.simulated_day for obs in observations} == {1, 2, 3}


def test_run_to_completion_resumes_from_the_persisted_current_step(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(engine, current_step=2, total_steps=3)
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion("sim_test"))

    definition = SimulationRepository(engine).get("sim_test")
    assert definition is not None
    assert definition.current_step == 3
    assert definition.status == SimulationStatus.COMPLETED

    observations = ObservationRepository(engine).list_for_greenhouse("gh_test")
    assert {obs.simulated_day for obs in observations} == {3}


def test_run_to_completion_is_a_noop_when_already_completed(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(engine, current_step=3, total_steps=3)
    definition = SimulationRepository(engine).get("sim_test")
    assert definition is not None
    SimulationRepository(engine).save(
        definition.model_copy(update={"status": SimulationStatus.COMPLETED})
    )
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion("sim_test"))

    assert EventRepository(engine).list_for_greenhouse("gh_test") == []
    assert ObservationRepository(engine).list_for_greenhouse("gh_test") == []
