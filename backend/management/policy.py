from typing import Protocol

from management.context import GreenhouseManagementContext
from management.validation.actions import RequestedAction
from simulation.scenarios.config import ScenarioConfig


class ManagementPolicy(Protocol):
    def decide(
        self, context: GreenhouseManagementContext, config: ScenarioConfig
    ) -> list[RequestedAction]: ...


class NoOpPolicy:
    def decide(
        self, context: GreenhouseManagementContext, config: ScenarioConfig
    ) -> list[RequestedAction]:
        return []
