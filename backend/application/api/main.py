import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from application.api.routers import greenhouses
from application.bootstrap import bootstrap_greenhouses
from application.db import create_engine_and_tables


def _database_url() -> str:
    return os.environ.get("GREENHOUSE_DATABASE_URL", "sqlite:///./data/greenhouse.db")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine_and_tables(_database_url())
    bootstrap_greenhouses(engine)
    app.state.engine = engine
    yield
    engine.dispose()


app = FastAPI(title="Greenhouse Insights API", lifespan=lifespan)
app.include_router(greenhouses.router)
