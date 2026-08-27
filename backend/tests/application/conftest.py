from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine

from application.db import create_engine_and_tables


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "greenhouse.db"


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    engine = create_engine_and_tables(f"sqlite:///{db_path}")
    yield engine
    engine.dispose()
