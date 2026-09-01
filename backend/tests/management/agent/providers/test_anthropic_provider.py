from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from domain.enums import PlantHealth
from domain.state import PlantState
from management.agent.providers.anthropic_provider import (
    AnthropicAgentModelProvider,
    _build_default_client,
)
from management.agent.tools import AgentToolkit
from management.context import GreenhouseManagementContext
from management.validation.actions import ScheduleInspectionAction, WaterPlantAction
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_ID = "gh_001_plant_001"
TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


@dataclass
class _ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _StubMessage:
    content: list[Any]


@dataclass
class _StubMessages:
    responses: list[_StubMessage]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def create(self, **kwargs: Any) -> _StubMessage:
        self.calls.append(kwargs)
        return self.responses[len(self.calls) - 1]


@dataclass
class _StubClient:
    responses: list[_StubMessage]

    def __post_init__(self) -> None:
        self.messages = _StubMessages(self.responses)


def _plant_state(**overrides: object) -> PlantState:
    defaults: dict[str, object] = dict(
        plant_id=PLANT_ID,
        greenhouse_id="gh_001",
        simulated_day=8,
        timestamp=TIMESTAMP,
        health=PlantHealth.HEALTHY,
    )
    defaults.update(overrides)
    return PlantState(**defaults)


def _context() -> GreenhouseManagementContext:
    return GreenhouseManagementContext(greenhouse_id="gh_001", day=8, plant_states=[_plant_state()])


def _toolkit(history: list[PlantState] | None = None, budget: int = 8) -> AgentToolkit:
    return AgentToolkit(
        _context(), history_reader=lambda plant_id, days: history or [], budget=budget
    )


def test_returns_the_submitted_actions_when_the_model_decides_immediately() -> None:
    submit = _ToolUseBlock(
        id="tu_1",
        name="submit_management_decision",
        input={"actions": [{"action_type": "WATER_PLANT", "plant_id": PLANT_ID, "amount_ml": 700}]},
    )
    client = _StubClient(responses=[_StubMessage(content=[submit])])
    provider = AnthropicAgentModelProvider(client=client)

    decision = provider.decide(_context(), _toolkit(), CONFIG)

    assert len(decision.actions) == 1
    assert isinstance(decision.actions[0], WaterPlantAction)
    assert decision.provider == "anthropic"
    assert len(client.messages.calls) == 1


def test_investigates_via_history_before_submitting() -> None:
    investigate = _ToolUseBlock(
        id="tu_1", name="get_plant_history", input={"plant_id": PLANT_ID, "days": 3}
    )
    submit = _ToolUseBlock(
        id="tu_2",
        name="submit_management_decision",
        input={
            "actions": [
                {
                    "action_type": "SCHEDULE_INSPECTION",
                    "plant_id": PLANT_ID,
                    "reason": "low moisture, single reading",
                }
            ]
        },
    )
    client = _StubClient(
        responses=[_StubMessage(content=[investigate]), _StubMessage(content=[submit])]
    )
    provider = AnthropicAgentModelProvider(client=client)
    toolkit = _toolkit()

    decision = provider.decide(_context(), toolkit, CONFIG)

    assert len(decision.actions) == 1
    assert isinstance(decision.actions[0], ScheduleInspectionAction)
    assert len(toolkit.calls) == 1
    assert toolkit.calls[0].tool == "get_plant_history"
    # the second call's tool_result carries the history back to the model
    second_call_messages = client.messages.calls[1]["messages"]
    assert second_call_messages[-1]["role"] == "user"


def test_forces_submission_once_the_tool_budget_is_exhausted() -> None:
    investigate = _ToolUseBlock(
        id="tu_1", name="get_plant_history", input={"plant_id": PLANT_ID, "days": 3}
    )
    submit = _ToolUseBlock(id="tu_2", name="submit_management_decision", input={"actions": []})
    client = _StubClient(
        responses=[_StubMessage(content=[investigate]), _StubMessage(content=[submit])]
    )
    provider = AnthropicAgentModelProvider(client=client)
    toolkit = _toolkit(budget=1)

    decision = provider.decide(_context(), toolkit, CONFIG)

    assert decision.actions == []
    second_call_kwargs = client.messages.calls[1]
    assert second_call_kwargs["tool_choice"] == {
        "type": "tool",
        "name": "submit_management_decision",
    }


def test_nudges_the_model_to_submit_if_it_replies_with_only_text() -> None:
    chatter = _StubMessage(content=[_TextBlock(text="Let me think about this.")])
    submit = _StubMessage(
        content=[_ToolUseBlock(id="tu_1", name="submit_management_decision", input={"actions": []})]
    )
    client = _StubClient(responses=[chatter, submit])
    provider = AnthropicAgentModelProvider(client=client)

    decision = provider.decide(_context(), _toolkit(), CONFIG)

    assert decision.actions == []
    assert len(client.messages.calls) == 2
    assert client.messages.calls[1]["tool_choice"] == {
        "type": "tool",
        "name": "submit_management_decision",
    }


def test_raises_if_the_model_never_submits_a_decision() -> None:
    chatter = _StubMessage(content=[_TextBlock(text="still thinking")])
    client = _StubClient(responses=[chatter] * 20)
    provider = AnthropicAgentModelProvider(client=client)

    with pytest.raises(RuntimeError, match="did not submit"):
        provider.decide(_context(), _toolkit(budget=1), CONFIG)


def test_rejects_a_malformed_submitted_action() -> None:
    submit = _ToolUseBlock(
        id="tu_1",
        name="submit_management_decision",
        # WATER_PLANT with no amount_ml - invalid per the action schema
        input={"actions": [{"action_type": "WATER_PLANT", "plant_id": PLANT_ID}]},
    )
    client = _StubClient(responses=[_StubMessage(content=[submit])])
    provider = AnthropicAgentModelProvider(client=client)

    with pytest.raises(ValidationError):
        provider.decide(_context(), _toolkit(), CONFIG)


def test_sends_the_configured_max_tokens() -> None:
    submit = _ToolUseBlock(id="tu_1", name="submit_management_decision", input={"actions": []})
    client = _StubClient(responses=[_StubMessage(content=[submit])])
    provider = AnthropicAgentModelProvider(client=client, max_tokens=256)

    provider.decide(_context(), _toolkit(), CONFIG)

    assert client.messages.calls[0]["max_tokens"] == 256


def test_default_client_carries_a_timeout_and_retry_cap() -> None:
    client = _build_default_client()

    assert client.timeout == 30.0
    assert client.max_retries == 2


def test_default_client_honors_env_var_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GREENHOUSE_AGENT_REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("GREENHOUSE_AGENT_MAX_RETRIES", "0")

    client = _build_default_client()

    assert client.timeout == 5.0
    assert client.max_retries == 0
