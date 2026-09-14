from pathlib import Path

from sqlalchemy import inspect

from application.db import create_engine_and_tables

EXPECTED_TABLES = {
    "greenhouses",
    "simulation_definitions",
    "observations",
    "events",
    "greenhouse_state_snapshots",
}


def test_create_engine_and_tables_creates_expected_tables(database_url: str) -> None:
    engine = create_engine_and_tables(database_url)

    table_names = set(inspect(engine).get_table_names())

    assert EXPECTED_TABLES <= table_names


def test_create_engine_and_tables_is_idempotent(database_url: str) -> None:
    create_engine_and_tables(database_url)
    engine = create_engine_and_tables(database_url)

    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= table_names


def test_create_engine_and_tables_creates_missing_parent_directories(tmp_path: Path) -> None:
    # SQLite-specific by nature: a file database needs its folder to exist.
    nested_db_path = tmp_path / "data" / "nested" / "greenhouse.db"

    engine = create_engine_and_tables(f"sqlite:///{nested_db_path}")

    assert nested_db_path.exists()
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
