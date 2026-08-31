from sqlalchemy import Engine, desc, select
from sqlalchemy.dialects.sqlite import insert

from application.persistence.schema import greenhouse_world_snapshots
from domain.world import GreenhouseWorld


class WorldRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, world: GreenhouseWorld) -> None:
        row = {
            "greenhouse_id": world.greenhouse_id,
            "simulated_day": world.simulated_day,
            "world_json": world.model_dump_json(),
        }
        statement = insert(greenhouse_world_snapshots).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["greenhouse_id", "simulated_day"],
            set_={"world_json": row["world_json"]},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get_latest(self, greenhouse_id: str) -> GreenhouseWorld | None:
        statement = (
            select(greenhouse_world_snapshots.c.world_json)
            .where(greenhouse_world_snapshots.c.greenhouse_id == greenhouse_id)
            .order_by(desc(greenhouse_world_snapshots.c.simulated_day))
            .limit(1)
        )
        with self._engine.connect() as connection:
            world_json = connection.execute(statement).scalar_one_or_none()
        return None if world_json is None else GreenhouseWorld.model_validate_json(world_json)
