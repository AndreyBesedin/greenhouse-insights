from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import Column, Connection, Engine, Integer, MetaData, String, Table, select

from application.persistence.upsert import UnsupportedDialect, upsert

_metadata = MetaData()
_pairs = Table(
    "pairs",
    _metadata,
    Column("left", String, primary_key=True),
    Column("right", String, primary_key=True),
    Column("count", Integer, nullable=False),
    Column("note", String, nullable=True),
)


@pytest.fixture
def pairs_engine(engine: Engine) -> Engine:
    _metadata.create_all(engine)
    return engine


def _rows(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(select(_pairs).order_by(_pairs.c.left)).mappings()
        ]


def test_upsert_inserts_a_new_row(pairs_engine: Engine) -> None:
    with pairs_engine.begin() as connection:
        upsert(connection, _pairs, {"left": "a", "right": "b", "count": 1}, key=("left", "right"))

    assert _rows(pairs_engine) == [{"left": "a", "right": "b", "count": 1, "note": None}]


def test_upsert_updates_every_non_key_column_on_conflict(pairs_engine: Engine) -> None:
    with pairs_engine.begin() as connection:
        upsert(
            connection,
            _pairs,
            {"left": "a", "right": "b", "count": 1, "note": "first"},
            key=("left", "right"),
        )
        upsert(
            connection,
            _pairs,
            {"left": "a", "right": "b", "count": 2, "note": None},
            key=("left", "right"),
        )
        upsert(connection, _pairs, {"left": "a", "right": "c", "count": 9}, key=("left", "right"))

    assert _rows(pairs_engine) == [
        {"left": "a", "right": "b", "count": 2, "note": None},
        {"left": "a", "right": "c", "count": 9, "note": None},
    ]


def test_upsert_rejects_a_dialect_it_has_no_implementation_for() -> None:
    # A dialect this project never uses: the failure must be loud rather
    # than a silently wrong statement.
    connection = cast(Connection, SimpleNamespace(dialect=SimpleNamespace(name="mysql")))
    with pytest.raises(UnsupportedDialect, match="mysql"):
        upsert(connection, _pairs, {"left": "a", "right": "b", "count": 1}, key=("left",))
