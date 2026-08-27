import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from application.api.routers import greenhouses, simulations
from application.bootstrap import bootstrap_greenhouses
from application.db import create_engine_and_tables
from application.simulation_service import SimulationService


def _database_url() -> str:
    return os.environ.get("GREENHOUSE_DATABASE_URL", "sqlite:///./data/greenhouse.db")


def _step_delay_seconds() -> float:
    return float(os.environ.get("GREENHOUSE_STEP_DELAY_SECONDS", "1.0"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine_and_tables(_database_url())
    bootstrap_greenhouses(engine)
    app.state.engine = engine
    app.state.simulation_service = SimulationService(
        engine, step_delay_seconds=_step_delay_seconds()
    )
    yield
    engine.dispose()


app = FastAPI(title="Greenhouse Insights API", lifespan=lifespan)
app.include_router(greenhouses.router)
app.include_router(simulations.router)
