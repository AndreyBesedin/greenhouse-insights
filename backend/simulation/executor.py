"""Pluggable execution of already-validated actions against the world.

Before this, simulation/runner.py called simulation.actions.apply_action
directly - the one and only way an accepted action could ever be carried
out. That conflated "the simulation executes actions" (true, and correct:
docs/design/greenhouse_agentic_management_design.md §45) with "there is
exactly one way execution happens" (an accident of how it was first built,
not a real constraint - the same design doc section explicitly expects
execution to be replaceable independently of who decided the action).

ActionExecutor makes that swap point real. SimulatedOperatorExecutor is the
only implementation so far: it executes instantaneously and completely
(waters the exact requested amount, harvests every ripe fruit in one pass),
which is the behavior simulation.actions.apply_action has always had. A
future SimulatedRobotExecutor (partial completion, delays, failure rates)
or a real executor (task creation, a robot/climate controller) implements
the same protocol; neither management/ nor simulation/runner.py would need
to change to add one.
"""

from datetime import datetime
from typing import Protocol

from domain.event import Event
from domain.world import GreenhouseWorld
from management.validation.actions import RequestedAction
from simulation.actions import apply_action
from simulation.scenarios.config import ScenarioConfig


class ActionExecutor(Protocol):
    def apply(
        self,
        world: GreenhouseWorld,
        action: RequestedAction,
        config: ScenarioConfig,
        *,
        day: int,
        timestamp: datetime,
    ) -> tuple[GreenhouseWorld, Event]: ...


class SimulatedOperatorExecutor:
    """Executes an accepted action instantaneously and completely."""

    def apply(
        self,
        world: GreenhouseWorld,
        action: RequestedAction,
        config: ScenarioConfig,
        *,
        day: int,
        timestamp: datetime,
    ) -> tuple[GreenhouseWorld, Event]:
        return apply_action(world, action, config, day=day, timestamp=timestamp)
