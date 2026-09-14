from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from domain.enums import SourceType
from domain.greenhouse import Compartment, Greenhouse, GreenhouseLayout, Plant


def _make_greenhouse(greenhouse_id: str = "gh_001") -> Greenhouse:
    return Greenhouse(
        greenhouse_id=greenhouse_id,
        name="Simulation Greenhouse 001",
        description="Primary demo greenhouse",
        source_type=SourceType.SIMULATION,
        crop="cherry_tomato",
        layout=GreenhouseLayout(rows=4, columns=10),
        plants=[
            Plant(plant_id="plant_001", variety="cherry_tomato", row=1, position_in_row=1),
            Plant(plant_id="plant_002", variety="cherry_tomato", row=1, position_in_row=2),
        ],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_save_then_get_round_trips_the_greenhouse(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    greenhouse = _make_greenhouse()

    repo.save(greenhouse)
    fetched = repo.get(greenhouse.greenhouse_id)

    assert fetched == greenhouse


def test_get_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)

    assert repo.get("does_not_exist") is None


def test_save_upserts_an_existing_greenhouse(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    greenhouse = _make_greenhouse()
    repo.save(greenhouse)

    updated = greenhouse.model_copy(update={"current_state_timestamp": datetime.now(UTC)})
    repo.save(updated)

    assert repo.get(greenhouse.greenhouse_id) == updated


def test_list_returns_all_saved_greenhouses(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    repo.save(_make_greenhouse("gh_001"))
    repo.save(_make_greenhouse("gh_002"))

    listed = repo.list()

    assert {gh.greenhouse_id for gh in listed} == {"gh_001", "gh_002"}


def test_delete_removes_the_greenhouse(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    repo.save(_make_greenhouse("gh_001"))
    repo.save(_make_greenhouse("gh_002"))

    repo.delete("gh_001")

    assert repo.get("gh_001") is None
    assert repo.get("gh_002") is not None


def test_delete_is_a_noop_for_an_unknown_greenhouse(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)

    repo.delete("does_not_exist")  # should not raise


def test_a_compartment_greenhouse_without_plants_round_trips(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    compartment = Greenhouse(
        greenhouse_id="wur_c306",
        name="Compartment 3.06",
        description="Recorded WUR compartment",
        source_type=SourceType.IMPORTED_DATA,
        crop="dwarf_tomato",
        layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
        plants=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    repo.save(compartment)

    assert repo.get("wur_c306") == compartment


def test_compartments_and_their_plants_round_trip(engine: Engine) -> None:
    repo = GreenhouseRepository(engine)
    greenhouse = Greenhouse(
        greenhouse_id="wur_agc4_2024",
        name="WUR AGC4 2024",
        description="Six recorded compartments",
        source_type=SourceType.IMPORTED_DATA,
        crop="dwarf_tomato",
        layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
        plants=[],
        compartments=[
            Compartment(
                compartment_id="3.06",
                name="Reference",
                description="team Reference, cam_1",
                plants=[Plant(plant_id="306-1", variety="dwarf_tomato", row=1, position_in_row=1)],
            ),
            Compartment(compartment_id="3.08", name="Trigger"),
        ],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    repo.save(greenhouse)
    fetched = repo.get("wur_agc4_2024")

    assert fetched == greenhouse
    assert fetched is not None and fetched.compartment("3.06") is not None
    assert [p.plant_id for p in fetched.all_plants] == ["306-1"]
