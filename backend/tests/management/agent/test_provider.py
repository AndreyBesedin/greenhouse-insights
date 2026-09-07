from datetime import UTC, datetime

from domain.enums import PlantHealth
from domain.state import PlantState
from management.agent.provider import AgentDecision, FakeAgentModelProvider
from management.agent.tools import AgentToolkit
from management.context import GreenhouseManagementContext
from management.validation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    ScheduleInspectionAction,
    WaterPlantAction,
)
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_ID = "gh_001_plant_001"
TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _plant_state(**overrides: object) -> PlantState:
    defaults: dict[str, object] = dict(
        plant_id=PLANT_ID,
        greenhouse_id="gh_001",
        simulated_day=8,
        timestamp=TIMESTAMP,
        health=PlantHealth.HEALTHY,
        latest_soil_moisture_pct=80.0,
    )
    defaults.update(overrides)
    return PlantState(**defaults)


def _decide(
    plant_state: PlantState, history: list[PlantState] | None = None
) -> tuple[AgentDecision, AgentToolkit]:
    context = GreenhouseManagementContext(greenhouse_id="gh_001", day=8, plant_states=[plant_state])
    toolkit = AgentToolkit(context, history_reader=lambda plant_id, days: history or [], budget=8)
    decision = FakeAgentModelProvider().decide(context, toolkit, CONFIG)
    return decision, toolkit


def test_does_not_investigate_or_water_a_well_watered_plant() -> None:
    decision, toolkit = _decide(_plant_state(latest_soil_moisture_pct=90.0))

    assert not any(isinstance(a, WaterPlantAction) for a in decision.actions)
    assert toolkit.calls == []  # adequate moisture needs no closer look


def test_harvests_once_enough_fruit_is_ripe() -> None:
    decision, _ = _decide(
        _plant_state(latest_ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold)
    )

    assert any(isinstance(a, HarvestPlantAction) for a in decision.actions)


def test_lowers_a_tall_plant() -> None:
    decision, _ = _decide(
        _plant_state(latest_visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 10)
    )

    assert any(isinstance(a, LowerPlantAction) for a in decision.actions)


def test_investigates_a_single_low_reading_via_history_before_deciding() -> None:
    """A single low-moisture reading is ambiguous (could be noise) - it
    must be investigated before acting, regardless of plant condition."""
    plant = _plant_state(latest_soil_moisture_pct=10.0)

    decision, toolkit = _decide(plant, history=[])

    assert any(call.tool == "get_plant_history" for call in toolkit.calls)
    # a single low reading with no sustained history should not trigger watering yet
    assert not any(isinstance(a, WaterPlantAction) for a in decision.actions)
    assert any(isinstance(a, ScheduleInspectionAction) for a in decision.actions)


def test_waters_once_low_moisture_is_sustained_in_history() -> None:
    plant = _plant_state(latest_soil_moisture_pct=10.0)
    sustained_history = [_plant_state(latest_soil_moisture_pct=8.0)]

    decision, _ = _decide(plant, history=sustained_history)

    assert any(isinstance(a, WaterPlantAction) for a in decision.actions)


def test_schedules_inspection_for_a_non_healthy_condition_without_a_tool_call() -> None:
    """A plant condition concern (PR 3) is its own reason to inspect - no
    history check needed, since the concern is the reconstructed condition
    itself, not something ambiguous evidence needs confirming."""
    plant = _plant_state(health=PlantHealth.MONITOR, latest_soil_moisture_pct=80.0)

    decision, toolkit = _decide(plant)

    assert any(isinstance(a, ScheduleInspectionAction) for a in decision.actions)
    assert toolkit.calls == []


def test_does_not_schedule_inspection_for_a_healthy_plant() -> None:
    decision, _ = _decide(_plant_state(health=PlantHealth.HEALTHY, latest_soil_moisture_pct=80.0))

    assert not any(isinstance(a, ScheduleInspectionAction) for a in decision.actions)


def test_schedules_inspection_when_budget_is_exhausted_before_investigating() -> None:
    plant = _plant_state(latest_soil_moisture_pct=10.0)
    context = GreenhouseManagementContext(greenhouse_id="gh_001", day=8, plant_states=[plant])
    toolkit = AgentToolkit(context, history_reader=lambda plant_id, days: [], budget=0)

    decision = FakeAgentModelProvider().decide(context, toolkit, CONFIG)

    assert any(isinstance(a, ScheduleInspectionAction) for a in decision.actions)
    assert not any(isinstance(a, WaterPlantAction) for a in decision.actions)
