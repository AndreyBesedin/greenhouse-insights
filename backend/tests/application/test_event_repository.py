from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from domain.enums import EventSource, EventType
from domain.event import Event


def _make_event(plant_id: str, simulated_day: int, event_id: str) -> Event:
    return Event(
        event_id=event_id,
        greenhouse_id="gh_001",
        plant_id=plant_id,
        simulated_day=simulated_day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        event_type=EventType.WATERING,
        source=EventSource.SIMULATION,
    )


def test_save_many_then_list_round_trips_events(engine: Engine) -> None:
    repo = EventRepository(engine)
    repo.save_many([_make_event("plant_017", 8, "evt_1"), _make_event("plant_017", 9, "evt_2")])

    listed = repo.list_for_greenhouse("gh_001")

    assert {e.event_id for e in listed} == {"evt_1", "evt_2"}


def test_list_for_greenhouse_filters_by_plant_id(engine: Engine) -> None:
    repo = EventRepository(engine)
    repo.save_many([_make_event("plant_001", 1, "evt_a"), _make_event("plant_002", 1, "evt_b")])

    listed = repo.list_for_greenhouse("gh_001", plant_id="plant_001")

    assert [e.event_id for e in listed] == ["evt_a"]


def test_list_for_greenhouse_never_returns_days_beyond_max_day(engine: Engine) -> None:
    repo = EventRepository(engine)
    repo.save_many([_make_event("plant_017", day, f"evt_day_{day}") for day in range(1, 6)])

    listed = repo.list_for_greenhouse("gh_001", plant_id="plant_017", max_day=3)

    assert {e.simulated_day for e in listed} == {1, 2, 3}


def test_event_parameters_round_trip_through_persistence(engine: Engine) -> None:
    repo = EventRepository(engine)
    event = _make_event("plant_017", 12, "evt_harvest").model_copy(
        update={
            "event_type": EventType.HARVEST,
            "source": EventSource.INFERRED_FROM_OBSERVATIONS,
            "confidence": 0.94,
            "parameters": {"estimated_mass_g": 820},
        }
    )

    repo.save_many([event])

    (listed,) = repo.list_for_greenhouse("gh_001")
    assert listed.confidence == 0.94
    assert listed.parameters == {"estimated_mass_g": 820}
