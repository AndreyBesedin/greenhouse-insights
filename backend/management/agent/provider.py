import os
from typing import Literal, Protocol

from pydantic import BaseModel

from domain.state import PlantState
from management.agent.tools import AgentToolkit, ToolBudgetExceededError
from management.context import GreenhouseManagementContext
from management.validation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    ScheduleInspectionAction,
    WaterPlantAction,
)
from simulation.scenarios.config import ScenarioConfig

_HISTORY_WINDOW_DAYS = 3
_SUSTAINED_LOW_MOISTURE_DAYS = 2


class AgentDecision(BaseModel):
    actions: list[RequestedAction]
    provider: str
    model: str


class AgentModelProvider(Protocol):
    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: ScenarioConfig
    ) -> AgentDecision: ...


class FakeAgentModelProvider:
    """A deterministic stand-in behind the AgentModelProvider interface.

    No LLM calls — this exists so the agentic policy, tool-calling loop, and
    tracing are real and testable without provider credentials. A real
    Anthropic/OpenAI adapter implementing the same protocol is a drop-in
    replacement (see build_default_provider()).

    Still genuinely uses the tools: harvest/lower are unambiguous mechanical
    actions decided directly from the current reading. Watering is the one
    ambiguous case - a single low-moisture reading could be noise - so it is
    investigated via get_plant_history first and only acted on if the low
    reading is sustained across recent days; otherwise it schedules an
    inspection instead of guessing, per the design doc's "when evidence is
    ambiguous, prefer inspection or no action". This reads the plant's own
    soil-moisture reading (environment data), not PlantState.health -
    plant condition and "does this evidence need a closer look" are
    different questions (docs/design/domain_model_eval_refactor_plan.md
    PR 2).
    """

    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: ScenarioConfig
    ) -> AgentDecision:
        actions: list[RequestedAction] = []

        for plant in context.plant_states:
            actions.extend(self._harvest_and_lower_actions(plant, config))
            actions.extend(self._watering_decision(plant, toolkit, config))

        return AgentDecision(actions=actions, provider="fake", model="scripted-v1")

    def _watering_decision(
        self, plant: PlantState, toolkit: AgentToolkit, config: ScenarioConfig
    ) -> list[RequestedAction]:
        looks_low = (
            plant.latest_soil_moisture_pct is not None
            and plant.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
        )
        if not looks_low:
            return []

        try:
            history = toolkit.get_plant_history(plant.plant_id, _HISTORY_WINDOW_DAYS)
        except ToolBudgetExceededError:
            return [
                ScheduleInspectionAction(
                    plant_id=plant.plant_id,
                    reason="unable to investigate within the tool-call budget",
                )
            ]

        low_moisture_readings = [
            entry
            for entry in [*history, plant]
            if entry.latest_soil_moisture_pct is not None
            and entry.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
        ]
        if len(low_moisture_readings) >= _SUSTAINED_LOW_MOISTURE_DAYS:
            return [WaterPlantAction(plant_id=plant.plant_id, amount_ml=config.watering_amount_ml)]
        return [
            ScheduleInspectionAction(
                plant_id=plant.plant_id,
                reason="soil moisture below threshold but not yet sustained",
            )
        ]

    def _harvest_and_lower_actions(
        self, plant: PlantState, config: ScenarioConfig
    ) -> list[RequestedAction]:
        actions: list[RequestedAction] = []
        if (
            plant.latest_ripe_fruit_count is not None
            and plant.latest_ripe_fruit_count >= config.harvest_ripe_fruit_count_threshold
        ):
            actions.append(HarvestPlantAction(plant_id=plant.plant_id))
        if (
            plant.latest_visible_height_cm is not None
            and plant.latest_visible_height_cm > config.lower_plant_height_threshold_cm
        ):
            actions.append(
                LowerPlantAction(plant_id=plant.plant_id, amount_cm=config.lower_plant_amount_cm)
            )
        return actions


def build_default_provider() -> AgentModelProvider:
    """The single swap point for a real LLM-backed provider.

    Selected via GREENHOUSE_AGENT_PROVIDER ("fake", the default, or
    "anthropic"). The default preserves all existing behavior - nothing
    calls a real model unless explicitly opted in.
    """
    provider_name = os.environ.get("GREENHOUSE_AGENT_PROVIDER", "fake")
    if provider_name == "anthropic":
        from management.agent.providers.anthropic_provider import AnthropicAgentModelProvider

        return AnthropicAgentModelProvider()
    if provider_name != "fake":
        raise ValueError(f"unknown GREENHOUSE_AGENT_PROVIDER: {provider_name!r}")
    return FakeAgentModelProvider()


class AgentProviderStatus(BaseModel):
    """What build_default_provider() would currently select, for the
    frontend to show an honest status instead of a static hint that never
    reflected whether a real provider was actually configured."""

    status: Literal["FAKE", "CONFIGURED", "MISCONFIGURED"]
    provider: str
    model: str | None = None
    detail: str | None = None


def describe_agent_provider() -> AgentProviderStatus:
    """Reports the same GREENHOUSE_AGENT_PROVIDER selection
    build_default_provider() would make, without constructing the provider -
    constructing AnthropicAgentModelProvider builds a real Anthropic API
    client and can raise if ANTHROPIC_API_KEY is missing, which this must
    not do just to report status."""
    provider_name = os.environ.get("GREENHOUSE_AGENT_PROVIDER", "fake")
    if provider_name == "fake":
        return AgentProviderStatus(status="FAKE", provider=provider_name)
    if provider_name == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return AgentProviderStatus(
                status="MISCONFIGURED",
                provider=provider_name,
                detail="GREENHOUSE_AGENT_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.",
            )
        from management.agent.providers.anthropic_provider import DEFAULT_MODEL

        model = os.environ.get("GREENHOUSE_AGENT_MODEL", DEFAULT_MODEL)
        return AgentProviderStatus(status="CONFIGURED", provider=provider_name, model=model)
    return AgentProviderStatus(
        status="MISCONFIGURED",
        provider=provider_name,
        detail=f"unknown GREENHOUSE_AGENT_PROVIDER: {provider_name!r}",
    )
