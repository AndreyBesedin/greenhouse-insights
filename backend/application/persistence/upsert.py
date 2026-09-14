"""Insert-or-update for whichever database the engine is bound to.

SQLAlchemy Core has no portable upsert: `ON CONFLICT DO UPDATE` is built by
the SQLite and PostgreSQL dialect modules separately. Every repository used
to import the SQLite one directly, which tied the whole persistence layer
to SQLite; this helper picks the dialect at execution time so the same
repositories run on both (docs/design/wur_execution_plan.md, step B1).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Connection, Table
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.sql import Executable


class UnsupportedDialect(Exception):
    pass


def upsert(
    connection: Connection,
    table: Table,
    row: Mapping[str, Any],
    *,
    key: Sequence[str],
) -> None:
    """Inserts `row`, or, if a row with the same `key` columns exists,
    updates every other column of it to the values in `row`."""
    update = {column: value for column, value in row.items() if column not in key}
    dialect = connection.dialect.name
    statement: Executable
    if dialect == "sqlite":
        statement = (
            sqlite.insert(table)
            .values(**row)
            .on_conflict_do_update(index_elements=list(key), set_=update)
        )
    elif dialect == "postgresql":
        statement = (
            postgresql.insert(table)
            .values(**row)
            .on_conflict_do_update(index_elements=list(key), set_=update)
        )
    else:
        raise UnsupportedDialect(f"no upsert implementation for dialect {dialect!r}")
    connection.execute(statement)
