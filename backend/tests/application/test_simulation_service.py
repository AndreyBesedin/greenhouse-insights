import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.simulation_service import SimulationService
from domain.enums import SimulationStatus, SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from simulation.definitions import SimulationDefinition
from simulation.scenarios import SCENARIO_REGISTRY


def _seed(
    engine: Engine, *, total_steps: int = 3, status: SimulationStatus = SimulationStatus.NOT_STARTED
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
    SimulationRepository(engine).save(
        SimulationDefinition(
            simulation_id="sim_test",
            greenhouse_id="gh_test",
            scenario_definition="gh_002",
            start_date=date(2026, 1, 1),
            duration_days=total_steps,
            random_seed=42,
            status=status,
            current_step=total_steps if status == SimulationStatus.COMPLETED else 0,
            total_steps=total_steps,
        )
    )


def test_start_simulation_runs_it_to_completion_exactly_once(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine, step_delay_seconds=0)

    async def scenario() -> None:
        await service.start_simulation("sim_test")
        await service.start_simulation("sim_test")
        task = service._tasks["sim_test"]
        await task

    asyncio.run(scenario())

    final = service.get_status("sim_test")
    assert final is not None
    assert final.status == SimulationStatus.COMPLETED
    assert final.current_step == 3


def test_start_simulation_reuses_the_in_flight_task(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine, step_delay_seconds=0.05)

    async def scenario() -> tuple[object, object]:
        await service.start_simulation("sim_test")
        first_task = service._tasks["sim_test"]
        await service.start_simulation("sim_test")
        second_task = service._tasks["sim_test"]
        await first_task
        return first_task, second_task

    first_task, second_task = asyncio.run(scenario())
    assert first_task is second_task


def test_start_simulation_is_a_noop_when_already_completed(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.COMPLETED)
    service = SimulationService(engine, step_delay_seconds=0)

    async def scenario() -> None:
        await service.start_simulation("sim_test")

    asyncio.run(scenario())

    assert not service.is_running("sim_test")
    final = service.get_status("sim_test")
    assert final is not None
    assert final.current_step == 3


def test_get_status_returns_none_for_unknown_simulation(engine: Engine) -> None:
    service = SimulationService(engine)

    assert service.get_status("does_not_exist") is None


def test_cancel_stops_an_in_flight_simulation(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine, step_delay_seconds=5)

    async def scenario() -> None:
        await service.start_simulation("sim_test")
        assert service.is_running("sim_test")
        service.cancel("sim_test")
        await asyncio.sleep(0)

    asyncio.run(scenario())

    assert not service.is_running("sim_test")


def test_cancel_is_a_noop_when_nothing_is_running(engine: Engine) -> None:
    service = SimulationService(engine)

    service.cancel("does_not_exist")  # should not raise
