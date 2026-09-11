from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import Engine

from application.persistence.state_repository import StateRepository
from domain.enums import PlantHealth
from domain.state import GreenhouseState, PlantState

DAY_ONE = datetime(2026, 1, 1, tzinfo=UTC)


def _at(day: int) -> datetime:
    return DAY_ONE + timedelta(days=day - 1)


def _make_state(day: int) -> GreenhouseState:
    plant_state = PlantState(
        plant_id="plant_017",
        greenhouse_id="gh_001",
        timestamp=_at(day),
        health=PlantHealth.HEALTHY,
    )
    return GreenhouseState.aggregate(
        greenhouse_id="gh_001",
        timestamp=_at(day),
        plant_states=[plant_state],
    )


def test_save_then_get_at_round_trips_a_snapshot(engine: Engine) -> None:
    repo = StateRepository(engine)
    state = _make_state(8)

    repo.save(state)

    assert repo.get_at("gh_001", at=_at(8)) == state


def test_get_at_returns_the_latest_snapshot_at_or_before_the_instant(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(5))
    repo.save(_make_state(8))

    between = repo.get_at("gh_001", at=_at(6))

    assert between is not None
    assert between.timestamp == _at(5)


def test_get_at_returns_none_before_the_first_snapshot(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(8))

    assert repo.get_at("gh_001", at=_at(7)) is None


def test_get_at_normalises_the_instant_to_utc_before_comparing(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(8))

    # 02:00 at UTC+2 is exactly _at(8) (midnight UTC) - the snapshot must be visible.
    same_instant_local = _at(8).astimezone(timezone(timedelta(hours=2)))
    assert same_instant_local.hour == 2

    assert repo.get_at("gh_001", at=same_instant_local) is not None


def test_get_latest_returns_the_most_recent_snapshot(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(5))
    repo.save(_make_state(8))
    repo.save(_make_state(3))

    latest = repo.get_latest("gh_001")

    assert latest is not None
    assert latest.timestamp == _at(8)


def test_get_latest_returns_none_when_nothing_saved(engine: Engine) -> None:
    repo = StateRepository(engine)

    assert repo.get_latest("gh_001") is None


def test_save_overwrites_the_snapshot_for_the_same_instant(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(3))
    replacement = _make_state(3).model_copy(update={"plants_healthy": 99})

    repo.save(replacement)

    assert repo.list_timestamps("gh_001") == [_at(3)]
    assert repo.get_latest("gh_001") == replacement


def test_list_up_to_returns_states_in_ascending_time_order(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(3))
    repo.save(_make_state(1))
    repo.save(_make_state(2))

    states = repo.list_up_to("gh_001", up_to=_at(3))

    assert [s.timestamp for s in states] == [_at(1), _at(2), _at(3)]


def test_list_up_to_never_returns_snapshots_after_the_instant(engine: Engine) -> None:
    repo = StateRepository(engine)
    for day in range(1, 6):
        repo.save(_make_state(day))

    states = repo.list_up_to("gh_001", up_to=_at(3))

    assert [s.timestamp for s in states] == [_at(1), _at(2), _at(3)]


def test_list_up_to_returns_empty_list_when_nothing_saved(engine: Engine) -> None:
    repo = StateRepository(engine)

    assert repo.list_up_to("gh_001", up_to=_at(10)) == []


def test_list_timestamps_returns_every_snapshot_instant_ascending(engine: Engine) -> None:
    repo = StateRepository(engine)
    repo.save(_make_state(2))
    repo.save(_make_state(1))

    assert repo.list_timestamps("gh_001") == [_at(1), _at(2)]
    assert repo.list_timestamps("gh_other") == []


def test_delete_for_greenhouse_removes_all_of_that_greenhouses_snapshots(engine: Engine) -> None:
    repo = StateRepository(engine)
    for day in range(1, 4):
        repo.save(_make_state(day))

    repo.delete_for_greenhouse("gh_001")

    assert repo.list_up_to("gh_001", up_to=_at(10)) == []
    assert repo.get_latest("gh_001") is None
