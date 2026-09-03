from collections.abc import Callable

from domain.management_trace import ToolCallTrace
from domain.state import PlantState
from management.context import GreenhouseManagementContext

PlantHistoryReader = Callable[[str, int], list[PlantState]]


class ToolBudgetExceededError(RuntimeError):
    """Raised when a policy tries to make more tool calls than its budget allows."""


class AgentToolkit:
    """The read tools an agentic policy may use, with call recording and a budget.

    Matches the agentic-management design doc's read-tool set (§7-9): plant
    state is looked up from the observable context (no hidden truth), plant
    history goes through a runner-provided reader backed by persisted,
    already-observable GreenhouseState snapshots.
    """

    def __init__(
        self,
        context: GreenhouseManagementContext,
        history_reader: PlantHistoryReader,
        *,
        budget: int,
        on_call: Callable[[ToolCallTrace], None] | None = None,
    ) -> None:
        self._context = context
        self._history_reader = history_reader
        self.budget = budget
        self._on_call = on_call
        self.calls: list[ToolCallTrace] = []

    def get_plant_state(self, plant_id: str) -> PlantState | None:
        self._consume_budget()
        state = self._context.plant_state(plant_id)
        summary = f"health={state.health}" if state is not None else "not found"
        self._record(
            ToolCallTrace(tool="get_plant_state", args={"plant_id": plant_id}, summary=summary)
        )
        return state

    def get_plant_history(self, plant_id: str, days: int) -> list[PlantState]:
        self._consume_budget()
        history = self._history_reader(plant_id, days)
        self._record(
            ToolCallTrace(
                tool="get_plant_history",
                args={"plant_id": plant_id, "days": days},
                summary=f"{len(history)} day(s) returned",
            )
        )
        return history

    def _record(self, trace: ToolCallTrace) -> None:
        self.calls.append(trace)
        if self._on_call is not None:
            self._on_call(trace)

    def _consume_budget(self) -> None:
        if len(self.calls) >= self.budget:
            raise ToolBudgetExceededError(f"tool-call budget of {self.budget} exceeded")
