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


def test_create_engine_and_tables_creates_expected_tables(tmp_path: Path) -> None:
    engine = create_engine_and_tables(f"sqlite:///{tmp_path / 'greenhouse.db'}")

    table_names = set(inspect(engine).get_table_names())

    assert EXPECTED_TABLES <= table_names


def test_create_engine_and_tables_is_idempotent(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'greenhouse.db'}"

    create_engine_and_tables(db_url)
    engine = create_engine_and_tables(db_url)

    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= table_names
