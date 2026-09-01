from typing import Protocol

from pydantic import BaseModel

from domain.enums import PlantHealth
from domain.state import PlantState
from simulation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    ScheduleInspectionAction,
    WaterPlantAction,
)
from simulation.agent.context import GreenhouseManagementContext
from simulation.agent.tools import AgentToolkit, ToolBudgetExceededError
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

    Still genuinely uses the tools: plants already known HEALTHY are acted on
    directly from the initial context (no need to investigate the obvious),
    but anything else is investigated via get_plant_history first, and only
    watered if the low-moisture reading is sustained across recent days —
    otherwise it schedules an inspection instead of guessing, per the design
    doc's "when evidence is ambiguous, prefer inspection or no action".
    """

    def decide(
        self, context: GreenhouseManagementContext, toolkit: AgentToolkit, config: ScenarioConfig
    ) -> AgentDecision:
        actions: list[RequestedAction] = []

        for plant in context.plant_states:
            if plant.health == PlantHealth.HEALTHY:
                actions.extend(self._mechanical_actions(plant, config))
                continue

            try:
                history = toolkit.get_plant_history(plant.plant_id, _HISTORY_WINDOW_DAYS)
            except ToolBudgetExceededError:
                actions.append(
                    ScheduleInspectionAction(
                        plant_id=plant.plant_id,
                        reason="unable to investigate within the tool-call budget",
                    )
                )
                continue

            actions.extend(self._investigated_actions(plant, history, config))

        return AgentDecision(actions=actions, provider="fake", model="scripted-v1")

    def _mechanical_actions(
        self, plant: PlantState, config: ScenarioConfig
    ) -> list[RequestedAction]:
        actions: list[RequestedAction] = []
        if (
            plant.latest_soil_moisture_pct is not None
            and plant.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
        ):
            actions.append(
                WaterPlantAction(plant_id=plant.plant_id, amount_ml=config.watering_amount_ml)
            )
        actions.extend(self._harvest_and_lower_actions(plant, config))
        return actions

    def _investigated_actions(
        self, plant: PlantState, history: list[PlantState], config: ScenarioConfig
    ) -> list[RequestedAction]:
        actions: list[RequestedAction] = []
        low_moisture_readings = [
            entry
            for entry in [*history, plant]
            if entry.latest_soil_moisture_pct is not None
            and entry.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
        ]
        if len(low_moisture_readings) >= _SUSTAINED_LOW_MOISTURE_DAYS:
            actions.append(
                WaterPlantAction(plant_id=plant.plant_id, amount_ml=config.watering_amount_ml)
            )
        elif (
            plant.latest_soil_moisture_pct is not None
            and plant.latest_soil_moisture_pct < config.watering_trigger_reservoir_pct
        ):
            actions.append(
                ScheduleInspectionAction(
                    plant_id=plant.plant_id,
                    reason="soil moisture below threshold but not yet sustained",
                )
            )
        actions.extend(self._harvest_and_lower_actions(plant, config))
        return actions

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
    """The single swap point for a real LLM-backed provider."""
    return FakeAgentModelProvider()
