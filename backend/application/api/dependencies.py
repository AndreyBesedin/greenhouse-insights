from fastapi import Request
from sqlalchemy import Engine

from application.simulation_service import SimulationService


def get_engine(request: Request) -> Engine:
    engine: Engine = request.app.state.engine
    return engine


def get_simulation_service(request: Request) -> SimulationService:
    service: SimulationService = request.app.state.simulation_service
    return service
