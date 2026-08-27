from sqlalchemy import Engine, create_engine

from application.persistence.schema import metadata


def create_engine_and_tables(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    metadata.create_all(engine, checkfirst=True)
    return engine
