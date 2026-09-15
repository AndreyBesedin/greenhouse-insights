import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.api.auth import AuthSettings, install_auth_error_handlers
from application.api.routers import (
    admin,
    greenhouses,
    me,
    organizations,
    recommendations,
    simulations,
    system,
)
from application.bootstrap import bootstrap_greenhouses
from application.db import create_engine_and_tables
from application.simulation_service import SimulationService

# Walks up from this file's directory looking for a .env file, so this finds
# backend/.env regardless of the working directory uvicorn was started from.
# Real environment variables (e.g. set in a deploy environment) always take
# precedence - load_dotenv never overwrites a variable that is already set.
load_dotenv()


def _database_url() -> str:
    return os.environ.get("GREENHOUSE_DATABASE_URL", "sqlite:///./data/greenhouse.db")


def _step_delay_seconds() -> float:
    return float(os.environ.get("GREENHOUSE_STEP_DELAY_SECONDS", "1.0"))


def _allowed_origins() -> list[str]:
    origins = os.environ.get("GREENHOUSE_ALLOWED_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Read before touching the database so a misconfigured deployment
    # fails fast instead of serving anything.
    app.state.auth_settings = AuthSettings.from_env()
    app.state.authenticator = app.state.auth_settings.authenticator()
    engine = create_engine_and_tables(_database_url())
    bootstrap_greenhouses(engine)
    app.state.engine = engine
    app.state.simulation_service = SimulationService(
        engine, step_delay_seconds=_step_delay_seconds()
    )
    yield
    engine.dispose()


app = FastAPI(title="Greenhouse Insights API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
install_auth_error_handlers(app)
app.include_router(me.router)
app.include_router(organizations.router)
app.include_router(admin.router)
app.include_router(greenhouses.router)
app.include_router(simulations.router)
app.include_router(recommendations.router)
app.include_router(system.router)
