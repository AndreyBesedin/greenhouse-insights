from sqlalchemy import Engine

from application.persistence.world_repository import WorldRepository
from domain.world import GreenhouseWorld
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.world_builder import advance_world, initialize_world

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_IDS = ["gh_001_plant_001"]


def _make_world(day: int) -> GreenhouseWorld:
    world = initialize_world(CONFIG, PLANT_IDS)
    for d in range(1, day + 1):
        world = advance_world(world, CONFIG, d)
    return world


def test_save_then_get_latest_round_trips_the_world(engine: Engine) -> None:
    repo = WorldRepository(engine)
    world = _make_world(5)

    repo.save(world)

    assert repo.get_latest("gh_001") == world


def test_get_latest_returns_none_when_nothing_saved(engine: Engine) -> None:
    repo = WorldRepository(engine)

    assert repo.get_latest("gh_001") is None


def test_get_latest_returns_the_most_recently_saved_day(engine: Engine) -> None:
    repo = WorldRepository(engine)
    repo.save(_make_world(3))
    repo.save(_make_world(8))

    latest = repo.get_latest("gh_001")

    assert latest is not None
    assert latest.simulated_day == 8
