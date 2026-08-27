from datetime import date, timedelta

from pydantic import BaseModel

from domain.enums import SimulationStatus


class SimulationDefinition(BaseModel):
    simulation_id: str
    greenhouse_id: str
    scenario_definition: str
    start_date: date
    duration_days: int
    step_duration: timedelta = timedelta(days=1)
    random_seed: int
    status: SimulationStatus = SimulationStatus.NOT_STARTED
    current_step: int = 0
    total_steps: int
