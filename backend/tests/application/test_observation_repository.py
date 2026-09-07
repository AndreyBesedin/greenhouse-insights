from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.observation_repository import ObservationRepository
from domain.enums import ObservationType, SourceType
from domain.observation import Observation
from domain.provenance import RecordSource


def _make_observation(plant_id: str, simulated_day: int, observation_id: str) -> Observation:
    return Observation(
        observation_id=observation_id,
        greenhouse_id="gh_001",
        plant_id=plant_id,
        simulated_day=simulated_day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        observation_type=ObservationType.SOIL_MOISTURE_PCT,
        value=38.0,
        source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_001"),
    )


def test_save_many_then_list_round_trips_observations(engine: Engine) -> None:
    repo = ObservationRepository(engine)
    observations = [
        _make_observation("plant_017", 8, "obs_1"),
        _make_observation("plant_017", 9, "obs_2"),
    ]

    repo.save_many(observations)

    listed = repo.list_for_greenhouse("gh_001")
    assert {o.observation_id for o in listed} == {"obs_1", "obs_2"}


def test_list_for_greenhouse_filters_by_plant_id(engine: Engine) -> None:
    repo = ObservationRepository(engine)
    repo.save_many(
        [
            _make_observation("plant_001", 1, "obs_a"),
            _make_observation("plant_002", 1, "obs_b"),
        ]
    )

    listed = repo.list_for_greenhouse("gh_001", plant_id="plant_001")

    assert [o.observation_id for o in listed] == ["obs_a"]


def test_list_for_greenhouse_never_returns_days_beyond_max_day(engine: Engine) -> None:
    repo = ObservationRepository(engine)
    repo.save_many([_make_observation("plant_017", day, f"obs_day_{day}") for day in range(1, 6)])

    listed = repo.list_for_greenhouse("gh_001", plant_id="plant_017", max_day=3)

    assert {o.simulated_day for o in listed} == {1, 2, 3}


def test_list_for_greenhouse_orders_by_simulated_day(engine: Engine) -> None:
    repo = ObservationRepository(engine)
    repo.save_many(
        [
            _make_observation("plant_017", 3, "obs_c"),
            _make_observation("plant_017", 1, "obs_a"),
            _make_observation("plant_017", 2, "obs_b"),
        ]
    )

    listed = repo.list_for_greenhouse("gh_001", plant_id="plant_017")

    assert [o.observation_id for o in listed] == ["obs_a", "obs_b", "obs_c"]


def test_delete_for_greenhouse_removes_only_that_greenhouses_observations(engine: Engine) -> None:
    repo = ObservationRepository(engine)
    repo.save_many([_make_observation("plant_017", 1, "obs_gh_001")])
    other = Observation(
        observation_id="obs_gh_002",
        greenhouse_id="gh_002",
        plant_id="plant_001",
        simulated_day=1,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        observation_type=ObservationType.SOIL_MOISTURE_PCT,
        value=40.0,
        source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_002"),
    )
    repo.save_many([other])

    repo.delete_for_greenhouse("gh_001")

    assert repo.list_for_greenhouse("gh_001") == []
    assert [o.observation_id for o in repo.list_for_greenhouse("gh_002")] == ["obs_gh_002"]
