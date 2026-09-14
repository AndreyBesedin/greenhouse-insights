import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, make_url, text

from application.db import create_engine_and_tables

TEST_DATABASE_URL_ENV_VAR = "GREENHOUSE_TEST_DATABASE_URL"


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
def database_url(db_path: Path) -> Iterator[str]:
    """A URL to an empty database that belongs to this test alone.

    By default a fresh SQLite file under tmp_path (fast, no services). When
    GREENHOUSE_TEST_DATABASE_URL names a PostgreSQL server, a database is
    created on it for the test and dropped afterwards, so the same suite
    proves the persistence layer on the database production runs
    (docs/design/wur_execution_plan.md, step B2)."""
    server_url = os.environ.get(TEST_DATABASE_URL_ENV_VAR)
    if not server_url:
        yield f"sqlite:///{db_path}"
        return

    admin_url = make_url(server_url)
    if admin_url.get_backend_name() != "postgresql":
        raise RuntimeError(f"{TEST_DATABASE_URL_ENV_VAR} must be a postgresql:// URL")
    name = f"test_{uuid.uuid4().hex[:12]}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=None)
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield admin_url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine_and_tables(database_url)
    yield engine
    engine.dispose()
