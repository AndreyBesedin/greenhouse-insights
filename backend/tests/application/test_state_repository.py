from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.state_repository import StateRepository
from domain.enums import PlantHealth
from domain.state import GreenhouseState, PlantState


def _make_state(simulated_day: int) -> GreenhouseState:
    plant_state = PlantState(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        simulated_day=simulated_day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        health=PlantHealth.HEALTHY,
    )
    return GreenhouseState.aggregate(
        greenhouse_id="gh_001",
        simulated_day=simulated_day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        plant_states=[plant_state],
    )


def test_save_then_get_round_trips_a_days_state(engine: Engine) -> None:
    repo = StateRepository(engine)
    state = _make_state(8)

    repo.save(state)

    assert repo.get("gh_001", day=8) == state


def test_get_returns_none_for_a_day_that_was_never_saved(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(8))

    assert repo.get("gh_001", day=9) is None


def test_get_latest_returns_the_most_recent_saved_day(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(5))
    repo.save(_make_state(8))
    repo.save(_make_state(3))

    latest = repo.get_latest("gh_001")

    assert latest is not None
    assert latest.simulated_day == 8


def test_get_latest_returns_none_when_nothing_saved(engine: Engine) -> None:
    repo = StateRepository(engine)

    assert repo.get_latest("gh_001") is None
