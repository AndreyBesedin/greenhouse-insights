from pydantic import BaseModel
from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.simulation_repository import SimulationRepository
from domain.enums import SimulationStatus, SourceType
from domain.greenhouse import Greenhouse
from simulation.definitions import SimulationDefinition


class GreenhouseListItem(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    source_type: SourceType
    crop: str
    plant_count: int
    status: SimulationStatus
    current_step: int
    total_steps: int


class SimulationSummary(BaseModel):
    simulation_id: str
    status: SimulationStatus
    current_step: int
    total_steps: int


class GreenhouseDetail(BaseModel):
    greenhouse: Greenhouse
    simulation: SimulationSummary


class GreenhouseService:
    def __init__(self, engine: Engine) -> None:
        self._greenhouses = GreenhouseRepository(engine)
        self._simulations = SimulationRepository(engine)

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
            simulation=SimulationSummary(
                simulation_id=simulation.simulation_id,
                status=simulation.status,
                current_step=simulation.current_step,
                total_steps=simulation.total_steps,
            ),
        )

    def _simulation_for(self, greenhouse_id: str) -> SimulationDefinition:
        simulation = self._simulations.get(f"sim_{greenhouse_id}")
        if simulation is None:
            raise LookupError(f"no simulation definition found for greenhouse {greenhouse_id!r}")
        return simulation


def _list_item(greenhouse: Greenhouse, simulation: SimulationDefinition) -> GreenhouseListItem:
    return GreenhouseListItem(
        greenhouse_id=greenhouse.greenhouse_id,
        name=greenhouse.name,
        description=greenhouse.description,
        source_type=greenhouse.source_type,
        crop=greenhouse.plants[0].variety if greenhouse.plants else "unknown",
        plant_count=len(greenhouse.plants),
        status=simulation.status,
        current_step=simulation.current_step,
        total_steps=simulation.total_steps,
    )
