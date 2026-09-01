"""A real AgentModelProvider backed by the Anthropic Messages API.

Implements the tool-calling loop from docs/design/greenhouse_agentic_management_design.md
section 23: the model may call get_plant_state / get_plant_history any
number of times up to the configured budget, then must finalize its
decision by calling submit_management_decision exactly once. Forcing the
decision through a tool call (rather than parsing free text) keeps
parsing robust and matches "the agent must not invent unavailable
actions" - the schema is the only vocabulary it has.
"""

import os
from typing import Any

import anthropic
from pydantic import TypeAdapter

from management.agent.prompt import SYSTEM_PROMPT, render_context
from management.agent.provider import AgentDecision
from management.agent.tools import AgentToolkit, ToolBudgetExceededError
from management.context import GreenhouseManagementContext
from management.validation.actions import RequestedAction
from simulation.scenarios.config import ScenarioConfig

_DEFAULT_MODEL = "claude-sonnet-5"
_DEFAULT_MAX_TOKENS = 1536
_DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_RETRIES = 2
_ROUND_SAFETY_MARGIN = 3

_GET_PLANT_STATE_TOOL: dict[str, Any] = {
    "name": "get_plant_state",
    "description": "Look up the latest observable state for one plant in this greenhouse.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plant_id": {"type": "string", "description": "The plant_id to look up."},
        },
        "required": ["plant_id"],
    },
}

_GET_PLANT_HISTORY_TOOL: dict[str, Any] = {
    "name": "get_plant_history",
    "description": "Look up recent daily observable states for one plant, most recent "
    "last. Use this to check whether a concerning reading is sustained rather than a "
    "single noisy sample.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plant_id": {"type": "string", "description": "The plant_id to look up."},
            "days": {
                "type": "integer",
                "minimum": 1,
                "description": "How many recent days of history to return.",
            },
        },
        "required": ["plant_id", "days"],
    },
}

_SUBMIT_DECISION_TOOL: dict[str, Any] = {
    "name": "submit_management_decision",
    "description": "Finalize your decision for this greenhouse for today. Call this "
    "exactly once, after investigating whatever plants you needed to. Include one entry "
    "per plant that needs an action; omit plants that need nothing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": [
                                "WATER_PLANT",
                                "HARVEST_PLANT",
                                "LOWER_PLANT",
                                "SCHEDULE_INSPECTION",
                            ],
                        },
                        "plant_id": {"type": "string"},
                        "amount_ml": {
                            "type": "number",
                            "description": "Required for WATER_PLANT only.",
                        },
                        "amount_cm": {
                            "type": "number",
                            "description": "Required for LOWER_PLANT only.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Required for SCHEDULE_INSPECTION only.",
                        },
                    },
                    "required": ["action_type", "plant_id"],
                },
            },
        },
        "required": ["actions"],
    },
}

_TOOLS = [_GET_PLANT_STATE_TOOL, _GET_PLANT_HISTORY_TOOL, _SUBMIT_DECISION_TOOL]
_SUBMIT_TOOL_CHOICE = {"type": "tool", "name": "submit_management_decision"}
_ACTIONS_ADAPTER: TypeAdapter[list[RequestedAction]] = TypeAdapter(list[RequestedAction])


def _build_default_client() -> "anthropic.Anthropic":
    timeout = float(
        os.environ.get("GREENHOUSE_AGENT_REQUEST_TIMEOUT_SECONDS", _DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    max_retries = int(os.environ.get("GREENHOUSE_AGENT_MAX_RETRIES", _DEFAULT_MAX_RETRIES))
    return anthropic.Anthropic(timeout=timeout, max_retries=max_retries)


class AnthropicAgentModelProvider:
    """AgentModelProvider backed by a real Claude model via the Anthropic API.

    The client is injectable so tests never need a network call or a real
    API key - only build_default_provider() constructs a live client, and
    only when explicitly selected via GREENHOUSE_AGENT_PROVIDER.

    A default client built here (client=None) always carries a request
    timeout and a retry cap, so a hung or flaky call cannot stall a
    simulation indefinitely - a client passed in explicitly (real or a
    test stub) is used as-is, since its timeout/retry behavior is then the
    caller's responsibility.
    """

    def __init__(
        self, client: Any = None, model: str | None = None, max_tokens: int | None = None
    ) -> None:
        # Typed as Any rather than anthropic.Anthropic: tests inject a lightweight
        # stub exposing only .messages.create(...) so they never need a real API
        # key or network access, matching the type: ignore already at the call
        # site for the same reason.
        self._client = client if client is not None else _build_default_client()
        self._model = model or os.environ.get("GREENHOUSE_AGENT_MODEL", _DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(
            os.environ.get("GREENHOUSE_AGENT_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
        )

    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: ScenarioConfig
    ) -> AgentDecision:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": render_context(context, config)}
        ]
        tool_choice: dict[str, Any] = {"type": "auto"}
        max_rounds = config.agent_tool_call_budget + _ROUND_SAFETY_MARGIN

        for _ in range(max_rounds):
            # The SDK's param types are precise generated TypedDicts (tool_choice
            # alone is a 4-way discriminated union); plain dicts built here are
            # structurally correct at runtime but mypy cannot verify that against
            # dict[str, Any]. The response is validated with our own pydantic
            # models below, so this stays the only untyped boundary.
            response = self._client.messages.create(  # type: ignore[call-overload]
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=_TOOLS,
                tool_choice=tool_choice,
            )
            tool_use_blocks = [block for block in response.content if block.type == "tool_use"]

            submitted = next(
                (b for b in tool_use_blocks if b.name == "submit_management_decision"), None
            )
            if submitted is not None:
                actions = _ACTIONS_ADAPTER.validate_python(submitted.input.get("actions", []))
                return AgentDecision(actions=actions, provider="anthropic", model=self._model)

            if not tool_use_blocks:
                messages.append({"role": "assistant", "content": response.content})
                messages.append(
                    {
                        "role": "user",
                        "content": "You must call submit_management_decision to finalize "
                        "your decision for today.",
                    }
                )
                tool_choice = _SUBMIT_TOOL_CHOICE
                continue

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": self._run_tools(tool_use_blocks, toolkit)})
            budget_exhausted = len(toolkit.calls) >= toolkit.budget
            tool_choice = _SUBMIT_TOOL_CHOICE if budget_exhausted else {"type": "auto"}

        raise RuntimeError(f"agent did not submit a management decision within {max_rounds} rounds")

    def _run_tools(self, tool_use_blocks: list[Any], toolkit: AgentToolkit) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        budget_exhausted = False
        for block in tool_use_blocks:
            if budget_exhausted:
                results.append(self._error_result(block.id, "tool-call budget already exhausted"))
                continue
            try:
                content = self._execute_tool(block, toolkit)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
            except ToolBudgetExceededError as exc:
                budget_exhausted = True
                results.append(self._error_result(block.id, str(exc)))
        return results

    def _execute_tool(self, block: Any, toolkit: AgentToolkit) -> str:
        if block.name == "get_plant_state":
            state = toolkit.get_plant_state(block.input["plant_id"])
            return state.model_dump_json() if state is not None else "null"
        if block.name == "get_plant_history":
            history = toolkit.get_plant_history(block.input["plant_id"], int(block.input["days"]))
            return "[" + ",".join(s.model_dump_json() for s in history) + "]"
        raise ValueError(f"unknown tool requested by the model: {block.name!r}")

    def _error_result(self, tool_use_id: str, message: str) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": message,
            "is_error": True,
        }
