from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine

from application.db import create_engine_and_tables


@pytest.fixture(autouse=True)
def _fake_agent_provider_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never depend on GREENHOUSE_AGENT_PROVIDER from the real
    environment or a developer's .env file - otherwise the suite can
    silently start making real, billed calls to a live LLM provider.
    (This happened: application.api.main loads .env at import time, so a
    developer .env with GREENHOUSE_AGENT_PROVIDER=anthropic leaked into
    later tests that assumed the default fake provider.) monkeypatch
    restores the prior value after every test automatically.
    """
    monkeypatch.setenv("GREENHOUSE_AGENT_PROVIDER", "fake")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "greenhouse.db"


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    engine = create_engine_and_tables(f"sqlite:///{db_path}")
    yield engine
    engine.dispose()
