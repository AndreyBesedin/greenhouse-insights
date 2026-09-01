from sqlalchemy import Engine

from application.persistence.scenario_config_repository import ScenarioConfigRepository
from simulation.scenarios import SCENARIO_REGISTRY


def test_save_then_get_round_trips_a_config(engine: Engine) -> None:
    repo = ScenarioConfigRepository(engine)
    config = SCENARIO_REGISTRY["gh_001"]

    repo.save(config)

    assert repo.get("gh_001") == config


def test_get_returns_none_when_nothing_saved(engine: Engine) -> None:
    repo = ScenarioConfigRepository(engine)

    assert repo.get("does_not_exist") is None


def test_save_overwrites_an_existing_config(engine: Engine) -> None:
    repo = ScenarioConfigRepository(engine)
    repo.save(SCENARIO_REGISTRY["gh_001"])

    updated = SCENARIO_REGISTRY["gh_001"].model_copy(update={"random_seed": 999})
    repo.save(updated)

    assert repo.get("gh_001") == updated


def test_delete_removes_the_config(engine: Engine) -> None:
    repo = ScenarioConfigRepository(engine)
    repo.save(SCENARIO_REGISTRY["gh_001"])

    repo.delete("gh_001")

    assert repo.get("gh_001") is None


def test_delete_is_a_noop_for_an_unknown_greenhouse(engine: Engine) -> None:
    repo = ScenarioConfigRepository(engine)

    repo.delete("does_not_exist")  # should not raise
