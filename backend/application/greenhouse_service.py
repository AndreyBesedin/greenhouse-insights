import random
from datetime import UTC, date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import ManagementPolicyType, SimulationStatus, SourceType
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
    plant_count: int
    status: SimulationStatus | None
    current_step: int | None
    total_steps: int | None


class SimulationSummary(BaseModel):
    simulation_id: str
    status: SimulationStatus
    current_step: int
    total_steps: int
    management_policy: ManagementPolicyType


class GreenhouseDetail(BaseModel):
    greenhouse: Greenhouse
    simulation: SimulationSummary | None


class PlantDetail(BaseModel):
    plant: Plant
    state: PlantState | None


class TimelineSummary(BaseModel):
    total_days: int
    current_day: int


class CreateGreenhouseRequest(BaseModel):
    name: str
    description: str = ""
    source_type: SourceType
    crop: str
    rows: int = Field(gt=0, le=50)
    columns: int = Field(gt=0, le=50)
    duration_days: int | None = Field(default=None, gt=0, le=200)
    random_seed: int | None = None
    management_policy: ManagementPolicyType | None = None

    @model_validator(mode="after")
    def _require_duration_for_simulations(self) -> "CreateGreenhouseRequest":
        if self.source_type == SourceType.SIMULATION and self.duration_days is None:
            raise ValueError("duration_days is required when source_type is SIMULATION")
        return self


class GreenhouseService:
    def __init__(self, engine: Engine) -> None:
        self._greenhouses = GreenhouseRepository(engine)
        self._simulations = SimulationRepository(engine)
        self._states = StateRepository(engine)
        self._scenario_configs = ScenarioConfigRepository(engine)
        self._management_traces = ManagementTraceRepository(engine)
        self._observations = ObservationRepository(engine)
        self._events = EventRepository(engine)
        self._worlds = WorldRepository(engine)

    def list_greenhouses(self) -> list[GreenhouseListItem]:
        return [
            _list_item(greenhouse, self._simulation_for(greenhouse.greenhouse_id))
            for greenhouse in self._greenhouses.list()
        ]

    def get_greenhouse_detail(self, greenhouse_id: str) -> GreenhouseDetail | None:
        greenhouse = self._greenhouses.get(greenhouse_id)
        if greenhouse is None:
            return None
        simulation = self._simulation_for(greenhouse_id)
        return GreenhouseDetail(
            greenhouse=greenhouse,
            simulation=_to_summary(simulation) if simulation is not None else None,
        )

    def create_greenhouse(self, request: CreateGreenhouseRequest) -> GreenhouseDetail:
        greenhouse_id = f"gh_{uuid4().hex[:8]}"
        greenhouse = Greenhouse(
            greenhouse_id=greenhouse_id,
            name=request.name,
            description=request.description,
            source_type=request.source_type,
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
            )
            self._simulations.save(simulation)

        return GreenhouseDetail(
            greenhouse=greenhouse,
            simulation=_to_summary(simulation) if simulation is not None else None,
        )

    def get_state(self, greenhouse_id: str, *, day: int | None) -> GreenhouseState | None:
        if day is not None:
            return self._states.get(greenhouse_id, day=day)
        return self._states.get_latest(greenhouse_id)

    def get_plant_detail(
        self, greenhouse_id: str, plant_id: str, *, day: int | None
    ) -> PlantDetail | None:
        greenhouse = self._greenhouses.get(greenhouse_id)
        if greenhouse is None:
            return None
        plant = next((p for p in greenhouse.plants if p.plant_id == plant_id), None)
        if plant is None:
            return None

        greenhouse_state = self.get_state(greenhouse_id, day=day)
        plant_state = None
        if greenhouse_state is not None:
            plant_state = next(
                (s for s in greenhouse_state.plant_states if s.plant_id == plant_id), None
            )
        return PlantDetail(plant=plant, state=plant_state)

    def get_plant_history(
        self, greenhouse_id: str, plant_id: str, *, up_to_day: int
    ) -> list[PlantState] | None:
        greenhouse = self._greenhouses.get(greenhouse_id)
        if greenhouse is None:
            return None
        if not any(p.plant_id == plant_id for p in greenhouse.plants):
            return None

        states = self._states.list_up_to_day(greenhouse_id, max_day=up_to_day)
        return [
            plant_state
            for greenhouse_state in states
            for plant_state in greenhouse_state.plant_states
            if plant_state.plant_id == plant_id
        ]

    def get_timeline(self, greenhouse_id: str) -> TimelineSummary | None:
        if self._greenhouses.get(greenhouse_id) is None:
            return None
        simulation = self._simulation_for(greenhouse_id)
        if simulation is None:
            return None
        return TimelineSummary(
            total_days=simulation.total_steps, current_day=simulation.current_step
        )

    def get_management_history(self, greenhouse_id: str) -> list[ManagementTrace] | None:
        simulation = self._simulation_for(greenhouse_id)
        if simulation is None:
            return None
        return self._management_traces.list_for_simulation(simulation.simulation_id)

    def delete_greenhouse(self, greenhouse_id: str) -> bool:
        """Deletes a greenhouse and everything derived from it: its simulation
        definition and scenario config (if any), management traces, world and
        state snapshots, observations, and events. Returns False if the
        greenhouse did not exist."""
        if self._greenhouses.get(greenhouse_id) is None:
            return False

        simulation = self._simulation_for(greenhouse_id)
        if simulation is not None:
            self._management_traces.delete_for_simulation(simulation.simulation_id)
            self._simulations.delete(simulation.simulation_id)
        self._scenario_configs.delete(greenhouse_id)
        self._worlds.delete_for_greenhouse(greenhouse_id)
        self._states.delete_for_greenhouse(greenhouse_id)
        self._events.delete_for_greenhouse(greenhouse_id)
        self._observations.delete_for_greenhouse(greenhouse_id)
        self._greenhouses.delete(greenhouse_id)
        return True

    def _simulation_for(self, greenhouse_id: str) -> SimulationDefinition | None:
        return self._simulations.get(f"sim_{greenhouse_id}")


def _to_summary(simulation: SimulationDefinition) -> SimulationSummary:
    return SimulationSummary(
        simulation_id=simulation.simulation_id,
        status=simulation.status,
        current_step=simulation.current_step,
        total_steps=simulation.total_steps,
        management_policy=simulation.management_policy,
    )


def _list_item(
    greenhouse: Greenhouse, simulation: SimulationDefinition | None
) -> GreenhouseListItem:
    return GreenhouseListItem(
        greenhouse_id=greenhouse.greenhouse_id,
        name=greenhouse.name,
        description=greenhouse.description,
        source_type=greenhouse.source_type,
        crop=greenhouse.plants[0].variety if greenhouse.plants else "unknown",
        plant_count=len(greenhouse.plants),
        status=simulation.status if simulation is not None else None,
        current_step=simulation.current_step if simulation is not None else None,
        total_steps=simulation.total_steps if simulation is not None else None,
    )
