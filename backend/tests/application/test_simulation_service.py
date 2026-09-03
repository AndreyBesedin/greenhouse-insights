import asyncio
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.recommendation_repository import RecommendationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.world_repository import WorldRepository
from application.simulation_service import (
    PendingRecommendationsExist,
    RecommendationAlreadyReviewed,
    SimulationService,
)
from domain.enums import (
    ActionExecutorType,
    ApprovalSource,
    ManagementPolicyType,
    RecommendationStatus,
    SimulationStatus,
    SourceType,
)
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from domain.recommendation import Recommendation
from management.validation.actions import WaterPlantAction
from simulation.definitions import SimulationDefinition
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.world_builder import initialize_world

PLANT_ID = "gh_test_plant_001"


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


def _set_current_step(engine: Engine, day: int) -> None:
    repo = SimulationRepository(engine)
    definition = repo.get("sim_test")
    assert definition is not None
    repo.save(definition.model_copy(update={"current_step": day}))


def _seed_world(engine: Engine, day: int = 1) -> None:
    world = initialize_world(SCENARIO_REGISTRY["gh_002"], [PLANT_ID], greenhouse_id="gh_test")
    WorldRepository(engine).save(world.model_copy(update={"simulated_day": day}))


def _pending_recommendation(
    recommendation_id: str = "rec_1", *, amount_ml: float = 700
) -> Recommendation:
    return Recommendation(
        recommendation_id=recommendation_id,
        simulation_id="sim_test",
        greenhouse_id="gh_test",
        simulated_day=1,
        plant_id=PLANT_ID,
        action=WaterPlantAction(plant_id=PLANT_ID, amount_ml=amount_ml),
        source_policy=ManagementPolicyType.DETERMINISTIC,
        reason="Soil moisture low.",
        requested_at=datetime(2026, 1, 1, tzinfo=UTC),
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


def test_advance_one_day_advances_exactly_one_step(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine)

    async def scenario() -> SimulationDefinition | None:
        return await service.advance_one_day("sim_test")

    result = asyncio.run(scenario())

    assert result is not None
    assert result.current_step == 1
    assert result.status == SimulationStatus.RUNNING


def test_advance_one_day_called_repeatedly_stops_at_each_day(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine)

    async def scenario() -> list[SimulationDefinition | None]:
        # confirm_dismiss_remaining=True: this test is about the day clock
        # advancing, not about reviewing whatever the deterministic policy
        # happened to propose along the way.
        return [
            await service.advance_one_day("sim_test"),
            await service.advance_one_day("sim_test", confirm_dismiss_remaining=True),
            await service.advance_one_day("sim_test", confirm_dismiss_remaining=True),
        ]

    results = asyncio.run(scenario())

    assert [r.current_step if r else None for r in results] == [1, 2, 3]
    assert results[-1] is not None
    assert results[-1].status == SimulationStatus.COMPLETED


def test_advance_one_day_is_a_noop_once_completed(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.COMPLETED)
    service = SimulationService(engine)

    async def scenario() -> SimulationDefinition | None:
        return await service.advance_one_day("sim_test")

    result = asyncio.run(scenario())

    assert result is not None
    assert result.current_step == 3
    assert result.status == SimulationStatus.COMPLETED


def test_advance_one_day_returns_none_for_unknown_simulation(engine: Engine) -> None:
    service = SimulationService(engine)

    async def scenario() -> SimulationDefinition | None:
        return await service.advance_one_day("does_not_exist")

    assert asyncio.run(scenario()) is None


def test_advance_one_day_is_a_noop_while_auto_run_is_in_flight(engine: Engine) -> None:
    _seed(engine, total_steps=3)
    service = SimulationService(engine, step_delay_seconds=5)

    async def scenario() -> SimulationDefinition | None:
        await service.start_simulation("sim_test")
        assert service.is_running("sim_test")
        return await service.advance_one_day("sim_test")

    result = asyncio.run(scenario())

    # The auto-run task already advanced day 1 before we could check in -
    # the point of this test is that advance_one_day did not race it and
    # skip an extra day, not that zero days have happened yet.
    assert result is not None
    assert result.current_step <= 1


def test_advance_one_day_raises_when_the_current_day_has_pending_recommendations(
    engine: Engine,
) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> None:
        await service.advance_one_day("sim_test")

    with pytest.raises(PendingRecommendationsExist):
        asyncio.run(scenario())


def test_advance_one_day_dismisses_pending_recommendations_when_confirmed(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> SimulationDefinition | None:
        return await service.advance_one_day("sim_test", confirm_dismiss_remaining=True)

    result = asyncio.run(scenario())

    assert result is not None
    assert result.current_step == 2
    dismissed = RecommendationRepository(engine).get("rec_1")
    assert dismissed is not None
    assert dismissed.status == RecommendationStatus.DISMISSED
    assert dismissed.reviewed_at is not None


def test_approve_recommendation_executes_it_and_marks_it_executed(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> Recommendation | None:
        return await service.approve_recommendation("rec_1")

    result = asyncio.run(scenario())

    assert result is not None
    assert result.status == RecommendationStatus.EXECUTED
    assert result.approved_by == ApprovalSource.HUMAN
    assert result.executed_by == ActionExecutorType.SIMULATED_OPERATOR
    assert result.executed_at is not None

    world = WorldRepository(engine).get_latest("gh_test")
    assert world is not None
    assert world.plant(PLANT_ID).water_reservoir_ml > 0


def test_approve_recommendation_rejects_an_invalid_action_via_validator(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation(amount_ml=0))
    service = SimulationService(engine)

    async def scenario() -> Recommendation | None:
        return await service.approve_recommendation("rec_1")

    result = asyncio.run(scenario())

    assert result is not None
    assert result.status == RecommendationStatus.REJECTED_BY_VALIDATOR
    assert result.approved_by == ApprovalSource.HUMAN
    assert result.rejection_reason is not None
    assert result.executed_at is None


def test_dismiss_recommendation_marks_it_dismissed_without_executing(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> Recommendation | None:
        return await service.dismiss_recommendation("rec_1")

    result = asyncio.run(scenario())

    assert result is not None
    assert result.status == RecommendationStatus.DISMISSED
    assert result.reviewed_at is not None

    # Nothing executed - the reservoir stays at its untouched initial level.
    world = WorldRepository(engine).get_latest("gh_test")
    assert world is not None
    assert (
        world.plant(PLANT_ID).water_reservoir_ml
        == SCENARIO_REGISTRY["gh_002"].initial_water_reservoir_ml
    )


def test_approve_returns_none_for_unknown_recommendation(engine: Engine) -> None:
    service = SimulationService(engine)

    async def scenario() -> Recommendation | None:
        return await service.approve_recommendation("does_not_exist")

    assert asyncio.run(scenario()) is None


def test_dismiss_returns_none_for_unknown_recommendation(engine: Engine) -> None:
    service = SimulationService(engine)

    async def scenario() -> Recommendation | None:
        return await service.dismiss_recommendation("does_not_exist")

    assert asyncio.run(scenario()) is None


def test_approve_an_already_reviewed_recommendation_raises(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> None:
        await service.dismiss_recommendation("rec_1")
        await service.approve_recommendation("rec_1")

    with pytest.raises(RecommendationAlreadyReviewed):
        asyncio.run(scenario())


def test_dismiss_an_already_reviewed_recommendation_raises(engine: Engine) -> None:
    _seed(engine, total_steps=3, status=SimulationStatus.RUNNING)
    _set_current_step(engine, 1)
    _seed_world(engine, day=1)
    RecommendationRepository(engine).save(_pending_recommendation())
    service = SimulationService(engine)

    async def scenario() -> None:
        await service.approve_recommendation("rec_1")
        await service.dismiss_recommendation("rec_1")

    with pytest.raises(RecommendationAlreadyReviewed):
        asyncio.run(scenario())
