import random
from datetime import UTC, date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.audit import AuditAction, AuditEvent
from application.auth.authorizer import Action, Authorizer
from application.auth.models import SERRAPULSE_INTERNAL_ORGANIZATION_ID
from application.persistence.audit_repository import AuditRepository
from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.membership_repository import MembershipRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.recommendation_repository import RecommendationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import ActionExecutorType, ManagementPolicyType, SimulationStatus, SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant, build_grid_plants
from domain.management_trace import ManagementTrace
from domain.state import GreenhouseState, PlantState
from simulation.definitions import SimulationDefinition
from simulation.scenarios.config import ScenarioConfig


class GreenhouseListItem(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    source_type: SourceType
    crop: str
    # Individually identified plants, across every compartment.
    plant_count: int
    compartment_count: int
    status: SimulationStatus | None
    current_step: int | None
    total_steps: int | None
    management_policy: ManagementPolicyType | None


class SimulationSummary(BaseModel):
    simulation_id: str
    status: SimulationStatus
    current_step: int
    total_steps: int
    management_policy: ManagementPolicyType
    action_executor: ActionExecutorType


class GreenhouseDetail(BaseModel):
    greenhouse: Greenhouse
    simulation: SimulationSummary | None


class PlantDetail(BaseModel):
    plant: Plant
    state: PlantState | None


class TimelineSummary(BaseModel):
    """The instants a greenhouse can be viewed at: one per persisted state
    snapshot, ascending, plus which of them is "now". Source-agnostic - a
    simulation produces one checkpoint per simulated day, a recorded
    dataset one per replay checkpoint."""

    checkpoints: list[datetime]
    current_timestamp: datetime | None


# AGENTIC greenhouses make a real, billed LLM call per simulated day (each
# call itself covering every plant in the greenhouse in one prompt). These
# caps are deliberately tighter than the general SIMULATION limits above so
# a single greenhouse cannot silently rack up an unbounded number of live
# API calls or an unbounded per-call prompt size.
MAX_AGENTIC_DURATION_DAYS = 30
MAX_AGENTIC_PLANT_COUNT = 25


class UnknownOrganization(LookupError):
    def __init__(self, organization_id: str) -> None:
        self.organization_id = organization_id
        super().__init__(f"organization {organization_id!r} does not exist")


class AssignOrganizationRequest(BaseModel):
    organization_id: str


class CreateGreenhouseRequest(BaseModel):
    name: str
    description: str = ""
    # The owning tenant. None means the internal organization, until the
    # UI lets a platform admin pick one; the field becomes required then.
    organization_id: str | None = None
    source_type: SourceType
    crop: str
    rows: int = Field(gt=0, le=50)
    columns: int = Field(gt=0, le=50)
    duration_days: int | None = Field(default=None, gt=0, le=200)
    random_seed: int | None = None
    management_policy: ManagementPolicyType | None = None
    action_executor: ActionExecutorType | None = None

    @model_validator(mode="after")
    def _require_duration_for_simulations(self) -> "CreateGreenhouseRequest":
        if self.source_type == SourceType.SIMULATION and self.duration_days is None:
            raise ValueError("duration_days is required when source_type is SIMULATION")
        return self

    @model_validator(mode="after")
    def _cap_agentic_cost(self) -> "CreateGreenhouseRequest":
        if self.management_policy != ManagementPolicyType.AGENTIC:
            return self
        if self.duration_days is not None and self.duration_days > MAX_AGENTIC_DURATION_DAYS:
            raise ValueError(
                f"duration_days must be <= {MAX_AGENTIC_DURATION_DAYS} for an AGENTIC "
                "greenhouse (each simulated day makes a real, billed LLM call)"
            )
        if self.rows * self.columns > MAX_AGENTIC_PLANT_COUNT:
            raise ValueError(
                f"rows * columns must be <= {MAX_AGENTIC_PLANT_COUNT} for an AGENTIC "
                "greenhouse (every plant is included in each day's LLM prompt)"
            )
        return self


class GreenhouseService:
    """Greenhouse reads and writes for one actor. Every operation is
    authorized here against the greenhouse's organization, whoever calls
    (HTTP, CLI, a worker): a greenhouse the actor may not read is reported
    as absent (None/False, a 404 over HTTP) so identifiers cannot be
    probed across tenants; an action the actor may see but not perform
    raises Forbidden (docs/design/authentication_authorization_plan.md,
    "Authorization in application services")."""

    def __init__(self, engine: Engine, actor: ActorContext) -> None:
        self._actor = actor
        self._authorizer = Authorizer(MembershipRepository(engine))
        self._greenhouses = GreenhouseRepository(engine)
        self._simulations = SimulationRepository(engine)
        self._states = StateRepository(engine)
        self._scenario_configs = ScenarioConfigRepository(engine)
        self._management_traces = ManagementTraceRepository(engine)
        self._observations = ObservationRepository(engine)
        self._events = EventRepository(engine)
        self._worlds = WorldRepository(engine)
        self._recommendations = RecommendationRepository(engine)
        self._organizations = OrganizationRepository(engine)
        self._audit = AuditRepository(engine)

    def list_greenhouses(self) -> list[GreenhouseListItem]:
        """The greenhouses in every organization the actor may read."""
        visible = self._authorizer.visible_organization_ids(self._actor)
        greenhouses = (
            self._greenhouses.list()
            if visible is None
            else self._greenhouses.list_for_organizations(visible)
        )
        return [
            _list_item(greenhouse, self._simulation_for(greenhouse.greenhouse_id))
            for greenhouse in greenhouses
        ]

    def get_greenhouse_detail(self, greenhouse_id: str) -> GreenhouseDetail | None:
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return None
        simulation = self._simulation_for(greenhouse_id)
        return GreenhouseDetail(
            greenhouse=greenhouse,
            simulation=_to_summary(simulation) if simulation is not None else None,
        )

    def create_greenhouse(self, request: CreateGreenhouseRequest) -> GreenhouseDetail:
        organization_id = request.organization_id or SERRAPULSE_INTERNAL_ORGANIZATION_ID
        self._authorizer.require(self._actor, Action.GREENHOUSE_CREATE, organization_id)
        if self._organizations.get(organization_id) is None:
            raise UnknownOrganization(organization_id)
        greenhouse_id = f"gh_{uuid4().hex[:8]}"
        greenhouse = Greenhouse(
            greenhouse_id=greenhouse_id,
            organization_id=organization_id,
            name=request.name,
            description=request.description,
            source_type=request.source_type,
            crop=request.crop,
            layout=GreenhouseLayout(rows=request.rows, columns=request.columns),
            plants=build_grid_plants(greenhouse_id, request.crop, request.rows, request.columns),
            created_at=datetime.now(UTC),
        )
        self._greenhouses.save(greenhouse)

        simulation: SimulationDefinition | None = None
        if request.source_type == SourceType.SIMULATION:
            assert request.duration_days is not None  # enforced by the model validator
            seed = (
                request.random_seed
                if request.random_seed is not None
                else random.randint(1, 1_000_000)
            )
            config = ScenarioConfig(
                greenhouse_id=greenhouse_id,
                name=request.name,
                description=request.description,
                variety=request.crop,
                rows=request.rows,
                columns=request.columns,
                start_date=date.today(),
                duration_days=request.duration_days,
                random_seed=seed,
            )
            self._scenario_configs.save(config)
            simulation = SimulationDefinition(
                simulation_id=f"sim_{greenhouse_id}",
                greenhouse_id=greenhouse_id,
                scenario_definition=greenhouse_id,
                start_date=config.start_date,
                duration_days=request.duration_days,
                random_seed=seed,
                total_steps=request.duration_days,
                management_policy=request.management_policy or ManagementPolicyType.DETERMINISTIC,
                action_executor=request.action_executor or ActionExecutorType.SIMULATED_OPERATOR,
            )
            self._simulations.save(simulation)

        self._record(
            AuditAction.GREENHOUSE_CREATED,
            greenhouse,
            details={"name": greenhouse.name, "source_type": greenhouse.source_type.value},
        )
        return GreenhouseDetail(
            greenhouse=greenhouse,
            simulation=_to_summary(simulation) if simulation is not None else None,
        )

    def assign_organization(
        self, greenhouse_id: str, request: AssignOrganizationRequest
    ) -> GreenhouseDetail | None:
        """Moves a greenhouse to another organization (customer setup;
        platform admin only). None if the greenhouse is absent or not
        visible; raises UnknownOrganization for a bad target."""
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return None
        self._authorizer.require(self._actor, Action.GREENHOUSE_ASSIGN, greenhouse.organization_id)
        if self._organizations.get(request.organization_id) is None:
            raise UnknownOrganization(request.organization_id)
        if request.organization_id != greenhouse.organization_id:
            previous = greenhouse.organization_id
            greenhouse = greenhouse.model_copy(update={"organization_id": request.organization_id})
            self._greenhouses.save(greenhouse)
            self._record(
                AuditAction.GREENHOUSE_REASSIGNED,
                greenhouse,
                details={"previous_organization_id": previous},
            )
        simulation = self._simulation_for(greenhouse_id)
        return GreenhouseDetail(
            greenhouse=greenhouse,
            simulation=_to_summary(simulation) if simulation is not None else None,
        )

    def get_state(self, greenhouse_id: str, *, at: datetime | None) -> GreenhouseState | None:
        """The greenhouse as of `at`: the latest snapshot taken at or
        before it (the latest of all when `at` is None)."""
        if self._readable(greenhouse_id) is None:
            return None
        if at is not None:
            return self._states.get_at(greenhouse_id, at=at)
        return self._states.get_latest(greenhouse_id)

    def get_plant_detail(
        self, greenhouse_id: str, plant_id: str, *, at: datetime | None
    ) -> PlantDetail | None:
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return None
        plant = next((p for p in greenhouse.all_plants if p.plant_id == plant_id), None)
        if plant is None:
            return None

        greenhouse_state = self.get_state(greenhouse_id, at=at)
        plant_state = None
        if greenhouse_state is not None:
            plant_state = next(
                (s for s in greenhouse_state.plant_states if s.plant_id == plant_id), None
            )
        return PlantDetail(plant=plant, state=plant_state)

    def get_plant_history(
        self, greenhouse_id: str, plant_id: str, *, up_to: datetime
    ) -> list[PlantState] | None:
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return None
        if not any(p.plant_id == plant_id for p in greenhouse.all_plants):
            return None

        states = self._states.list_up_to(greenhouse_id, up_to=up_to)
        return [
            plant_state
            for greenhouse_state in states
            for plant_state in greenhouse_state.plant_states
            if plant_state.plant_id == plant_id
        ]

    def get_timeline(self, greenhouse_id: str) -> TimelineSummary | None:
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return None
        return TimelineSummary(
            checkpoints=self._states.list_timestamps(greenhouse_id),
            current_timestamp=greenhouse.current_state_timestamp,
        )

    def get_management_history(self, greenhouse_id: str) -> list[ManagementTrace] | None:
        if self._readable(greenhouse_id) is None:
            return None
        simulation = self._simulation_for(greenhouse_id)
        if simulation is None:
            return None
        return self._management_traces.list_for_simulation(simulation.simulation_id)

    def delete_greenhouse(self, greenhouse_id: str) -> bool:
        """Deletes a greenhouse and everything derived from it: its simulation
        definition and scenario config (if any), management traces, world and
        state snapshots, observations, events, and recommendations. Returns
        False if the greenhouse did not exist (or is not visible to the
        actor); raises Forbidden if it is visible but the actor may not
        delete it."""
        greenhouse = self._readable(greenhouse_id)
        if greenhouse is None:
            return False
        self._authorizer.require(self._actor, Action.GREENHOUSE_DELETE, greenhouse.organization_id)

        simulation = self._simulation_for(greenhouse_id)
        if simulation is not None:
            self._management_traces.delete_for_simulation(simulation.simulation_id)
            self._simulations.delete(simulation.simulation_id)
        self._scenario_configs.delete(greenhouse_id)
        self._worlds.delete_for_greenhouse(greenhouse_id)
        self._states.delete_for_greenhouse(greenhouse_id)
        self._events.delete_for_greenhouse(greenhouse_id)
        self._observations.delete_for_greenhouse(greenhouse_id)
        self._recommendations.delete_for_greenhouse(greenhouse_id)
        self._greenhouses.delete(greenhouse_id)
        self._record(AuditAction.GREENHOUSE_DELETED, greenhouse, details={"name": greenhouse.name})
        return True

    def _record(
        self, action: AuditAction, greenhouse: Greenhouse, *, details: dict[str, str]
    ) -> None:
        self._audit.append(
            AuditEvent(
                audit_id=f"aud_{uuid4().hex[:12]}",
                timestamp=datetime.now(UTC),
                actor_id=self._actor.actor_id,
                action=action,
                target_type="greenhouse",
                target_id=greenhouse.greenhouse_id,
                organization_id=greenhouse.organization_id,
                details=dict(details),
            )
        )

    def _simulation_for(self, greenhouse_id: str) -> SimulationDefinition | None:
        return self._simulations.get_by_greenhouse(greenhouse_id)

    def _readable(self, greenhouse_id: str) -> Greenhouse | None:
        """The greenhouse, if it exists and the actor may read it."""
        greenhouse = self._greenhouses.get(greenhouse_id)
        if greenhouse is None:
            return None
        if not self._authorizer.can(
            self._actor, Action.GREENHOUSE_READ, greenhouse.organization_id
        ):
            return None
        return greenhouse


def _to_summary(simulation: SimulationDefinition) -> SimulationSummary:
    return SimulationSummary(
        simulation_id=simulation.simulation_id,
        status=simulation.status,
        current_step=simulation.current_step,
        total_steps=simulation.total_steps,
        management_policy=simulation.management_policy,
        action_executor=simulation.action_executor,
    )


def _list_item(
    greenhouse: Greenhouse, simulation: SimulationDefinition | None
) -> GreenhouseListItem:
    return GreenhouseListItem(
        greenhouse_id=greenhouse.greenhouse_id,
        name=greenhouse.name,
        description=greenhouse.description,
        source_type=greenhouse.source_type,
        crop=greenhouse.crop
        or (greenhouse.all_plants[0].variety if greenhouse.all_plants else "unknown"),
        plant_count=len(greenhouse.all_plants),
        compartment_count=len(greenhouse.compartments),
        status=simulation.status if simulation is not None else None,
        current_step=simulation.current_step if simulation is not None else None,
        total_steps=simulation.total_steps if simulation is not None else None,
        management_policy=simulation.management_policy if simulation is not None else None,
    )
