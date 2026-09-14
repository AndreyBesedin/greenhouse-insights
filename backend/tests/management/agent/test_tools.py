from datetime import UTC, datetime

import pytest

from domain.enums import PlantHealth
from domain.management_trace import ToolCallTrace
from domain.state import PlantState
from management.agent.tools import AgentToolkit, ToolBudgetExceededError
from management.context import GreenhouseManagementContext

TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _plant_state(plant_id: str) -> PlantState:
    return PlantState(
        plant_id=plant_id,
        greenhouse_id="gh_001",
        timestamp=TIMESTAMP,
        health=PlantHealth.HEALTHY,
    )


def _context() -> GreenhouseManagementContext:
    return GreenhouseManagementContext(
        greenhouse_id="gh_001", timestamp=TIMESTAMP, plant_states=[_plant_state("plant_001")]
    )


def test_get_plant_state_returns_the_matching_state() -> None:
    toolkit = AgentToolkit(_context(), history_reader=lambda plant_id, days: [], budget=5)

    state = toolkit.get_plant_state("plant_001")

    assert state is not None
    assert state.plant_id == "plant_001"


def test_get_plant_state_returns_none_for_an_unknown_plant() -> None:
    toolkit = AgentToolkit(_context(), history_reader=lambda plant_id, days: [], budget=5)

    assert toolkit.get_plant_state("does_not_exist") is None


def test_get_plant_history_delegates_to_the_reader() -> None:
    history = [_plant_state("plant_001")]
    toolkit = AgentToolkit(_context(), history_reader=lambda plant_id, days: history, budget=5)

    result = toolkit.get_plant_history("plant_001", days=3)

    assert result == history


def test_calls_are_recorded() -> None:
    toolkit = AgentToolkit(_context(), history_reader=lambda plant_id, days: [], budget=5)

    toolkit.get_plant_state("plant_001")
    toolkit.get_plant_history("plant_001", days=3)

    assert [call.tool for call in toolkit.calls] == ["get_plant_state", "get_plant_history"]


def test_on_call_is_invoked_with_each_recorded_trace() -> None:
    seen: list[ToolCallTrace] = []
    toolkit = AgentToolkit(
        _context(), history_reader=lambda plant_id, days: [], budget=5, on_call=seen.append
    )

    toolkit.get_plant_state("plant_001")
    toolkit.get_plant_history("plant_001", days=3)

    assert [trace.tool for trace in seen] == ["get_plant_state", "get_plant_history"]


def test_exceeding_the_budget_raises() -> None:
    toolkit = AgentToolkit(_context(), history_reader=lambda plant_id, days: [], budget=1)

    toolkit.get_plant_state("plant_001")

    with pytest.raises(ToolBudgetExceededError):
        toolkit.get_plant_state("plant_001")
