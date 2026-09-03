import asyncio

from sqlalchemy import Engine

from application.persistence.simulation_repository import SimulationRepository
from domain.enums import SimulationStatus
from simulation.definitions import SimulationDefinition
from simulation.runner import SimulationRunner


class SimulationService:
    def __init__(self, engine: Engine, *, step_delay_seconds: float = 1.0) -> None:
        self._simulations = SimulationRepository(engine)
        self._runner = SimulationRunner(engine, step_delay_seconds=step_delay_seconds)
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start_simulation(self, simulation_id: str) -> SimulationDefinition | None:
        definition = self._simulations.get(simulation_id)
        if definition is None or definition.status == SimulationStatus.COMPLETED:
            return definition

        if not self.is_running(simulation_id):
            self._tasks[simulation_id] = asyncio.create_task(
                self._runner.run_to_completion(simulation_id)
            )
        return definition

    async def advance_one_day(self, simulation_id: str) -> SimulationDefinition | None:
        """Advances exactly one simulated day, then stops - the manual,
        human-in-the-loop counterpart to start_simulation's auto-run-to-
        completion. Returns the definition unchanged (a no-op) if the
        simulation does not exist, is already completed, or is currently
        auto-running via start_simulation."""
        definition = self._simulations.get(simulation_id)
        if definition is None or definition.status == SimulationStatus.COMPLETED:
            return definition
        if self.is_running(simulation_id):
            return definition

        next_day = definition.current_step + 1
        if next_day > definition.total_steps:
            return definition

        await asyncio.to_thread(self._runner.run_one_day, simulation_id, next_day)
        return self._simulations.get(simulation_id)

    def get_status(self, simulation_id: str) -> SimulationDefinition | None:
        return self._simulations.get(simulation_id)

    def is_running(self, simulation_id: str) -> bool:
        task = self._tasks.get(simulation_id)
        return task is not None and not task.done()

    def cancel(self, simulation_id: str) -> None:
        task = self._tasks.pop(simulation_id, None)
        if task is not None and not task.done():
            task.cancel()
