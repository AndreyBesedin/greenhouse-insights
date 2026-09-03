from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from domain.management_trace import ToolCallTrace
from management.agent.provider import AgentModelProvider
from management.agent.tools import AgentToolkit, PlantHistoryReader
from management.context import GreenhouseManagementContext
from management.validation.actions import RequestedAction
from simulation.scenarios.config import ScenarioConfig


class AgentRunSummary(BaseModel):
    """Everything the runner needs to build a persisted ManagementTrace,
    minus the fields (simulation_id, accepted/rejected counts) only the
    runner knows after validating the returned actions."""

    provider: str
    model: str
    tool_calls: list[ToolCallTrace]
    requested_action_count: int
    status: Literal["SUCCESS", "FAILED"]
    error: str | None
    started_at: datetime
    completed_at: datetime


class AgenticPolicy:
    """ManagementPolicy backed by an AgentModelProvider (real or fake).

    On provider failure, records it and requests no actions for the day
    rather than propagating — the simulation must keep running (design doc
    §40).
    """

    def __init__(self, provider: AgentModelProvider, history_reader: PlantHistoryReader) -> None:
        self._provider = provider
        self._history_reader = history_reader
        self.last_run: AgentRunSummary | None = None
        # Set by the runner before decide() when it wants high-level,
        # tool-call-derived progress updates for a currently-polling
        # frontend (docs/design/demo_readiness_plan.md section 14) - kept
        # off the shared ManagementPolicy.decide() signature since only the
        # agentic policy has anything meaningful to report mid-flight.
        self.progress_callback: Callable[[ToolCallTrace], None] | None = None

    def decide(
        self, context: GreenhouseManagementContext, config: ScenarioConfig
    ) -> list[RequestedAction]:
        started_at = datetime.now(UTC)
        toolkit = AgentToolkit(
            context,
            self._history_reader,
            budget=config.agent_tool_call_budget,
            on_call=self.progress_callback,
        )

        try:
            decision = self._provider.decide(context, toolkit, config)
            self.last_run = AgentRunSummary(
                provider=decision.provider,
                model=decision.model,
                tool_calls=toolkit.calls,
                requested_action_count=len(decision.actions),
                status="SUCCESS",
                error=None,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            return decision.actions
        except Exception as exc:  # a provider failure must not crash the simulation
            self.last_run = AgentRunSummary(
                provider="unknown",
                model="unknown",
                tool_calls=toolkit.calls,
                requested_action_count=0,
                status="FAILED",
                error=str(exc),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            return []
