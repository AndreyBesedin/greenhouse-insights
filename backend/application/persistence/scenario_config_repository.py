from sqlalchemy import Engine, delete, select

from application.persistence.schema import scenario_configs
from application.persistence.upsert import upsert
from simulation.scenarios.config import ScenarioConfig


class ScenarioConfigRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, config: ScenarioConfig) -> None:
        row = {
            "greenhouse_id": config.greenhouse_id,
            "config_json": config.model_dump_json(),
        }
        with self._engine.begin() as connection:
            upsert(connection, scenario_configs, row, key=("greenhouse_id",))

    def get(self, greenhouse_id: str) -> ScenarioConfig | None:
        statement = select(scenario_configs.c.config_json).where(
            scenario_configs.c.greenhouse_id == greenhouse_id
        )
        with self._engine.connect() as connection:
            config_json = connection.execute(statement).scalar_one_or_none()
        return None if config_json is None else ScenarioConfig.model_validate_json(config_json)

    def delete(self, greenhouse_id: str) -> None:
        statement = delete(scenario_configs).where(
            scenario_configs.c.greenhouse_id == greenhouse_id
        )
        with self._engine.begin() as connection:
            connection.execute(statement)
