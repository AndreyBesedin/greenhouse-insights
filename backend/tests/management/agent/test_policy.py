from datetime import UTC, datetime

from domain.enums import PlantHealth
from domain.state import PlantState
from management.agent.policy import AgenticPolicy
from management.agent.provider import AgentDecision
from management.agent.tools import AgentToolkit
from management.context import GreenhouseManagementContext
from management.validation.actions import RequestedAction, WaterPlantAction
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_ID = "gh_001_plant_001"
TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


class _StubProvider:
    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: object
    ) -> AgentDecision:
        toolkit.get_plant_state(PLANT_ID)
        return AgentDecision(
            actions=[WaterPlantAction(plant_id=PLANT_ID, amount_ml=500)],
            provider="stub",
            model="stub-v1",
        )


class _FailingProvider:
    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: object
    ) -> AgentDecision:
        raise RuntimeError("provider is unavailable")


def _context() -> GreenhouseManagementContext:
    plant_state = PlantState(
        plant_id=PLANT_ID,
        greenhouse_id="gh_001",
        simulated_day=8,
        timestamp=TIMESTAMP,
        health=PlantHealth.HEALTHY,
    )
    return GreenhouseManagementContext(greenhouse_id="gh_001", day=8, plant_states=[plant_state])


def test_agentic_policy_returns_the_providers_actions_and_records_a_successful_run() -> None:
    policy = AgenticPolicy(_StubProvider(), history_reader=lambda plant_id, days: [])

    actions: list[RequestedAction] = policy.decide(_context(), CONFIG)

    assert len(actions) == 1
    assert isinstance(actions[0], WaterPlantAction)
    assert policy.last_run is not None
    assert policy.last_run.status == "SUCCESS"
    assert policy.last_run.provider == "stub"
    assert len(policy.last_run.tool_calls) == 1


def test_agentic_policy_survives_a_provider_failure() -> None:
    policy = AgenticPolicy(_FailingProvider(), history_reader=lambda plant_id, days: [])

    actions = policy.decide(_context(), CONFIG)

    assert actions == []
    assert policy.last_run is not None
    assert policy.last_run.status == "FAILED"
    assert "unavailable" in (policy.last_run.error or "")


def test_agentic_policy_forwards_tool_calls_to_the_progress_callback() -> None:
    policy = AgenticPolicy(_StubProvider(), history_reader=lambda plant_id, days: [])
    seen = []
    policy.progress_callback = lambda trace: seen.append(trace.tool)

    policy.decide(_context(), CONFIG)

    assert seen == ["get_plant_state"]
