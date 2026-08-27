import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from domain.enums import SimulationStatus
from intelligence.state_reconstruction import (
    reconstruct_greenhouse_state,
    reconstruct_plant_state,
)
from simulation.generator import generate_day
from simulation.scenarios import SCENARIO_REGISTRY


class SimulationRunner:
    def __init__(self, engine: Engine, *, step_delay_seconds: float = 1.0) -> None:
        self._engine = engine
        self._step_delay_seconds = step_delay_seconds
        self._greenhouses = GreenhouseRepository(engine)
        self._simulations = SimulationRepository(engine)
        self._observations = ObservationRepository(engine)
        self._events = EventRepository(engine)
        self._states = StateRepository(engine)

    async def run_to_completion(self, simulation_id: str) -> None:
        while True:
            definition = self._simulations.get(simulation_id)
            if definition is None or definition.status == SimulationStatus.COMPLETED:
                return

            next_day = definition.current_step + 1
            if next_day > definition.total_steps:
                return

            await asyncio.to_thread(self._run_one_day, simulation_id, next_day)

            if next_day < definition.total_steps:
                await asyncio.sleep(self._step_delay_seconds)

    def _run_one_day(self, simulation_id: str, day: int) -> None:
        definition = self._simulations.get(simulation_id)
        if definition is None:
            raise LookupError(f"no simulation definition found for {simulation_id!r}")

        greenhouse = self._greenhouses.get(definition.greenhouse_id)
        if greenhouse is None:
            raise LookupError(f"no greenhouse found for {definition.greenhouse_id!r}")

        config = SCENARIO_REGISTRY[definition.scenario_definition]
        plant_ids = [plant.plant_id for plant in greenhouse.plants]
        timestamp = datetime.combine(definition.start_date, datetime.min.time(), tzinfo=UTC)
        timestamp += timedelta(days=day - 1)

        generation = generate_day(
            config, greenhouse.greenhouse_id, plant_ids, day=day, timestamp=timestamp
        )
        self._observations.save_many(generation.observations)
        self._events.save_many(generation.events)

        plant_states = [
            reconstruct_plant_state(
                plant_id=plant_id,
                greenhouse_id=greenhouse.greenhouse_id,
                day=day,
                timestamp=timestamp,
                observations=generation.observations,
                events=generation.events,
            )
            for plant_id in plant_ids
        ]
        greenhouse_state = reconstruct_greenhouse_state(
            greenhouse_id=greenhouse.greenhouse_id,
            day=day,
            timestamp=timestamp,
            plant_states=plant_states,
        )
        self._states.save(greenhouse_state)

        is_final_day = day == definition.total_steps
        updated_definition = definition.model_copy(
            update={
                "current_step": day,
                "status": SimulationStatus.COMPLETED if is_final_day else SimulationStatus.RUNNING,
            }
        )
        self._simulations.save(updated_definition)

        updated_greenhouse = greenhouse.model_copy(
            update={"current_state_timestamp": timestamp, "latest_available_timestamp": timestamp}
        )
        self._greenhouses.save(updated_greenhouse)
