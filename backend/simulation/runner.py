import asyncio
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import ActionExecutorType, ManagementPolicyType, SimulationStatus
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
from management.validation.actions import ActionResult, RequestedAction, validate_action
from simulation.executor import ActionExecutor, SimulatedOperatorExecutor
from simulation.observations import generate_observations
from simulation.world_builder import advance_world, initialize_world


class DayProposal(BaseModel):
    """What prepare_day produces: the world has evolved and the management
    policy has proposed actions, but nothing has been validated or executed
    yet - docs/design/demo_readiness_plan.md section 8's "important semantic
    decision" that advancing a day stops here until a human reviews it.
    """

    simulation_id: str
    greenhouse_id: str
    simulated_day: int
    timestamp: datetime
    management_policy: ManagementPolicyType
    proposed_actions: list[RequestedAction]
    plant_states_by_id: dict[str, PlantState]


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
        """Legacy auto-run, kept for the existing /run endpoint: proposes
        and immediately auto-approves every action every day, with no
        human review. Bypasses recommendation persistence entirely - do
        not use this path once the manual review flow is the primary one.
        """
        while True:
            definition = self._simulations.get(simulation_id)
            if definition is None or definition.status == SimulationStatus.COMPLETED:
                return

            next_day = definition.current_step + 1
            if next_day > definition.total_steps:
                return

            await asyncio.to_thread(self._run_and_auto_approve_one_day, simulation_id, next_day)

            if next_day < definition.total_steps:
                await asyncio.sleep(self._step_delay_seconds)

    def _run_and_auto_approve_one_day(self, simulation_id: str, day: int) -> None:
        proposal = self.prepare_day(simulation_id, day)
        for action in proposal.proposed_actions:
            self.execute_recommendation_action(simulation_id, day, action)
        self.refresh_day_state(simulation_id, day)

    def prepare_day(self, simulation_id: str, day: int) -> DayProposal:
        """Advances the world for one day, generates and persists its
        observations, and asks the management policy what it would like to
        do. Saves a pre-action GreenhouseState snapshot (observed state
        only) and advances current_step - the day genuinely is "current"
        for the whole review process, not just once it is fully resolved.
        Does not validate or execute anything.
        """
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

        self._observations.save_many(generation.observations)
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
                    # Accepted/rejected are decided per-recommendation, potentially
                    # long after this trace is written (or never, if dismissed) -
                    # query Recommendation rows for that ground truth instead.
                    accepted_action_count=0,
                    rejected_action_count=0,
                    status=run.status,
                    error=run.error,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                )
            )

        greenhouse_state = reconstruct_greenhouse_state(
            greenhouse_id=greenhouse.greenhouse_id,
            day=day,
            timestamp=timestamp,
            plant_states=[
                ps.model_copy(
                    update={"harvested_total_g": world.plant(ps.plant_id).cumulative_harvest_g}
                )
                for ps in observable_plant_states
            ],
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

        return DayProposal(
            simulation_id=simulation_id,
            greenhouse_id=greenhouse.greenhouse_id,
            simulated_day=day,
            timestamp=timestamp,
            management_policy=definition.management_policy,
            proposed_actions=actions,
            plant_states_by_id={ps.plant_id: ps for ps in observable_plant_states},
        )

    def execute_recommendation_action(
        self, simulation_id: str, day: int, action: RequestedAction
    ) -> ActionResult:
        """Validates one action against the current world and, if accepted,
        executes and persists it. Never trusts that the action is valid
        merely because a human approved it or an agent proposed it
        (docs/design/greenhouse_agentic_management_design.md section 19).
        """
        definition = self._simulations.get(simulation_id)
        if definition is None:
            raise LookupError(f"no simulation definition found for {simulation_id!r}")
        config = self._scenario_configs.get(definition.scenario_definition)
        if config is None:
            raise LookupError(f"no scenario config found for {definition.scenario_definition!r}")

        world = self._worlds.get_latest(definition.greenhouse_id)
        if world is None:
            raise LookupError(f"no world snapshot found for {definition.greenhouse_id!r}")

        result = validate_action(world, action)
        if not result.accepted:
            return result

        timestamp = datetime.combine(definition.start_date, datetime.min.time(), tzinfo=UTC)
        timestamp += timedelta(days=day - 1)

        executor = self._resolve_executor(definition.action_executor)
        world, event = executor.apply(world, action, config, day=day, timestamp=timestamp)

        self._events.save_many([event])
        self._worlds.save(world)

        return result

    def refresh_day_state(self, simulation_id: str, day: int) -> None:
        """Re-derives and re-saves day N's GreenhouseState from its
        observations, every event executed for it so far, and the current
        world. Idempotent and safe to call after every recommendation
        review - GreenhouseState is always a reconstruction, never
        hand-mutated (intelligence/state_reconstruction.py)."""
        definition = self._simulations.get(simulation_id)
        if definition is None:
            raise LookupError(f"no simulation definition found for {simulation_id!r}")
        greenhouse = self._greenhouses.get(definition.greenhouse_id)
        if greenhouse is None:
            raise LookupError(f"no greenhouse found for {definition.greenhouse_id!r}")
        world = self._worlds.get_latest(greenhouse.greenhouse_id)
        if world is None:
            raise LookupError(f"no world snapshot found for {greenhouse.greenhouse_id!r}")

        timestamp = datetime.combine(definition.start_date, datetime.min.time(), tzinfo=UTC)
        timestamp += timedelta(days=day - 1)
        plant_ids = [plant.plant_id for plant in greenhouse.plants]

        day_observations = [
            o
            for o in self._observations.list_for_greenhouse(greenhouse.greenhouse_id, max_day=day)
            if o.simulated_day == day
        ]
        day_events = [
            e
            for e in self._events.list_for_greenhouse(greenhouse.greenhouse_id, max_day=day)
            if e.simulated_day == day
        ]

        plant_states = [
            reconstruct_plant_state(
                plant_id=plant_id,
                greenhouse_id=greenhouse.greenhouse_id,
                day=day,
                timestamp=timestamp,
                observations=day_observations,
                events=day_events,
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

    def _resolve_executor(self, executor_type: ActionExecutorType) -> ActionExecutor:
        if executor_type == ActionExecutorType.SIMULATED_OPERATOR:
            return SimulatedOperatorExecutor()
        raise ValueError(f"unknown action executor type: {executor_type!r}")

    def _history_reader(self, greenhouse_id: str, *, up_to_day: int) -> PlantHistoryReader:
        def read(plant_id: str, days: int) -> list[PlantState]:
            if up_to_day < 1:
                return []
            states = self._states.list_up_to_day(greenhouse_id, max_day=up_to_day)
            matching = [ps for gs in states for ps in gs.plant_states if ps.plant_id == plant_id]
            return matching[-days:]

        return read
