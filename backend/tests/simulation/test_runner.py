import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from domain.enums import ManagementPolicyType, SimulationStatus, SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from domain.management_progress import ManagementProgress
from simulation.definitions import SimulationDefinition
from simulation.runner import SimulationRunner
from simulation.scenarios import SCENARIO_REGISTRY


def _seed_greenhouse_and_simulation(
    engine: Engine,
    *,
    current_step: int = 0,
    total_steps: int = 3,
    management_policy: ManagementPolicyType = ManagementPolicyType.DETERMINISTIC,
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
    ScenarioConfigRepository(engine).save(SCENARIO_REGISTRY["gh_002"])

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
        management_policy=management_policy,
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

    # One state snapshot and one batch of observations per simulated day,
    # stamped with the simulation clock's timestamp for that day.
    state_repo = StateRepository(engine)
    expected_instants = [definition.timestamp_for_step(day) for day in (1, 2, 3)]
    assert state_repo.list_timestamps("gh_test") == expected_instants

    observations = ObservationRepository(engine).list_for_greenhouse("gh_test")
    assert {obs.timestamp for obs in observations} == set(expected_instants)


def test_run_to_completion_resumes_from_the_persisted_current_step(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(engine, current_step=2, total_steps=3)
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion("sim_test"))

    definition = SimulationRepository(engine).get("sim_test")
    assert definition is not None
    assert definition.current_step == 3
    assert definition.status == SimulationStatus.COMPLETED

    observations = ObservationRepository(engine).list_for_greenhouse("gh_test")
    assert {obs.timestamp for obs in observations} == {definition.timestamp_for_step(3)}


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


def test_run_to_completion_with_agentic_policy_persists_traces_and_applies_actions(
    engine: Engine,
) -> None:
    _seed_greenhouse_and_simulation(
        engine, total_steps=8, management_policy=ManagementPolicyType.AGENTIC
    )
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion("sim_test"))

    definition = SimulationRepository(engine).get("sim_test")
    assert definition is not None
    assert definition.status == SimulationStatus.COMPLETED

    traces = ManagementTraceRepository(engine).list_for_simulation("sim_test")
    assert [t.simulated_day for t in traces] == list(range(1, 9))
    assert all(t.provider == "fake" for t in traces)
    assert all(t.status == "SUCCESS" for t in traces)

    # The plant starts around 50% soil moisture and drains over the run, so the
    # agent should investigate and/or act on it by day 8.
    events = EventRepository(engine).list_for_greenhouse("gh_test")
    assert events, "expected the agentic policy to take at least one action across 8 days"


def test_prepare_day_reports_progress_for_an_agentic_policy(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(
        engine, total_steps=8, management_policy=ManagementPolicyType.AGENTIC
    )
    runner = SimulationRunner(engine, step_delay_seconds=0)
    events: list[ManagementProgress] = []

    for day in range(1, 9):
        runner.prepare_day("sim_test", day, progress_reporter=events.append)

    assert events[0].phase == "ANALYZING"
    assert events[0].message == "Analysing greenhouse…"
    ready_events = [e for e in events if e.phase == "READY"]
    assert len(ready_events) == 8
    assert all(e.recommendation_count is not None for e in ready_events)
    assert any(
        "Checking" in e.message or "Inspecting" in e.message
        for e in events
        if e.phase == "ANALYZING"
    )


def test_prepare_day_reports_nothing_for_a_deterministic_policy(engine: Engine) -> None:
    _seed_greenhouse_and_simulation(engine, total_steps=1)
    runner = SimulationRunner(engine, step_delay_seconds=0)
    events: list[ManagementProgress] = []

    runner.prepare_day("sim_test", 1, progress_reporter=events.append)

    assert events == []
