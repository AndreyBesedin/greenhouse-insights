import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import ManagementPolicyType, SimulationStatus
from domain.event import Event
from domain.management_trace import ManagementTrace
from domain.state import PlantState
from intelligence.state_reconstruction import (
    reconstruct_greenhouse_state,
    reconstruct_plant_state,
)
from management.agent.policy import AgenticPolicy
from management.agent.provider import build_default_provider
from management.agent.tools import PlantHistoryReader
from management.context import GreenhouseManagementContext
from management.deterministic.policy import DeterministicPolicy
from management.policy import ManagementPolicy, NoOpPolicy
from management.validation.actions import validate_action
from simulation.actions import apply_action
from simulation.observations import generate_observations
from simulation.world_builder import advance_world, initialize_world


class SimulationRunner:
    def __init__(self, engine: Engine, *, step_delay_seconds: float = 1.0) -> None:
        self._engine = engine
        self._step_delay_seconds = step_delay_seconds
        self._greenhouses = GreenhouseRepository(engine)
        self._simulations = SimulationRepository(engine)
        self._observations = ObservationRepository(engine)
        self._events = EventRepository(engine)
        self._states = StateRepository(engine)
        self._worlds = WorldRepository(engine)
        self._scenario_configs = ScenarioConfigRepository(engine)
        self._management_traces = ManagementTraceRepository(engine)
        self._agent_provider = build_default_provider()

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

        config = self._scenario_configs.get(definition.scenario_definition)
        if config is None:
            raise LookupError(f"no scenario config found for {definition.scenario_definition!r}")
        plant_ids = [plant.plant_id for plant in greenhouse.plants]
        timestamp = datetime.combine(definition.start_date, datetime.min.time(), tzinfo=UTC)
        timestamp += timedelta(days=day - 1)

        world = self._worlds.get_latest(greenhouse.greenhouse_id)
        if world is None:
            world = initialize_world(config, plant_ids, greenhouse_id=greenhouse.greenhouse_id)
        world = advance_world(world, config, day)

        generation = generate_observations(world, config, day=day, timestamp=timestamp)

        observable_plant_states = [
            reconstruct_plant_state(
                plant_id=plant_id,
                greenhouse_id=greenhouse.greenhouse_id,
                day=day,
                timestamp=timestamp,
                observations=generation.observations,
                events=[],
            )
            for plant_id in plant_ids
        ]
        context = GreenhouseManagementContext(
            greenhouse_id=greenhouse.greenhouse_id, day=day, plant_states=observable_plant_states
        )

        policy = self._resolve_policy(definition.management_policy, greenhouse.greenhouse_id, day)
        actions = policy.decide(context, config)

        action_events: list[Event] = []
        accepted = 0
        rejected = 0
        for action in actions:
            result = validate_action(world, action)
            if not result.accepted:
                rejected += 1
                continue
            accepted += 1
            world, event = apply_action(world, action, config, day=day, timestamp=timestamp)
            action_events.append(event)

        self._observations.save_many(generation.observations)
        self._events.save_many(action_events)
        self._worlds.save(world)

        if isinstance(policy, AgenticPolicy) and policy.last_run is not None:
            run = policy.last_run
            self._management_traces.save(
                ManagementTrace(
                    simulation_id=simulation_id,
                    greenhouse_id=greenhouse.greenhouse_id,
                    simulated_day=day,
                    provider=run.provider,
                    model=run.model,
                    tool_calls=run.tool_calls,
                    requested_action_count=run.requested_action_count,
                    accepted_action_count=accepted,
                    rejected_action_count=rejected,
                    status=run.status,
                    error=run.error,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                )
            )

        plant_states = [
            reconstruct_plant_state(
                plant_id=plant_id,
                greenhouse_id=greenhouse.greenhouse_id,
                day=day,
                timestamp=timestamp,
                observations=generation.observations,
                events=action_events,
            ).model_copy(update={"harvested_total_g": world.plant(plant_id).cumulative_harvest_g})
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

    def _resolve_policy(
        self, policy_type: ManagementPolicyType, greenhouse_id: str, day: int
    ) -> ManagementPolicy:
        if policy_type == ManagementPolicyType.NONE:
            return NoOpPolicy()
        if policy_type == ManagementPolicyType.AGENTIC:
            return AgenticPolicy(
                self._agent_provider, self._history_reader(greenhouse_id, up_to_day=day - 1)
            )
        return DeterministicPolicy()

    def _history_reader(self, greenhouse_id: str, *, up_to_day: int) -> PlantHistoryReader:
        def read(plant_id: str, days: int) -> list[PlantState]:
            if up_to_day < 1:
                return []
            states = self._states.list_up_to_day(greenhouse_id, max_day=up_to_day)
            matching = [ps for gs in states for ps in gs.plant_states if ps.plant_id == plant_id]
            return matching[-days:]

        return read
