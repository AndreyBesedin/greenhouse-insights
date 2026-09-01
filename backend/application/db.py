from pathlib import Path

from sqlalchemy import Engine, create_engine

from alembic import command
from alembic.config import Config

_SQLITE_FILE_PREFIX = "sqlite:///"
ALEMBIC_INI_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"


def create_engine_and_tables(database_url: str) -> Engine:
    if database_url.startswith(_SQLITE_FILE_PREFIX):
        db_path = database_url.removeprefix(_SQLITE_FILE_PREFIX)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    return engine
