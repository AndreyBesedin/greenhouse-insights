from pathlib import Path

from sqlalchemy import Engine, create_engine

from application.persistence.schema import metadata

_SQLITE_FILE_PREFIX = "sqlite:///"


def create_engine_and_tables(database_url: str) -> Engine:
    if database_url.startswith(_SQLITE_FILE_PREFIX):
        db_path = database_url.removeprefix(_SQLITE_FILE_PREFIX)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    metadata.create_all(engine, checkfirst=True)
    return engine
