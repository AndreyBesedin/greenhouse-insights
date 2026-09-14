from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import Engine

from application.greenhouse_service import GreenhouseService
from domain.enums import ObservationType, PlantHealth, SourceType
from domain.greenhouse import Compartment, Greenhouse, GreenhouseLayout, Plant
from domain.observation import Observation
from domain.provenance import RecordSource
from ingestion.canonical import write_canonical_greenhouse
from ingestion.loader import load_canonical_greenhouse, reconstruct_checkpoints
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE

SOURCE = RecordSource(type=SourceType.IMPORTED_DATA, source_id="test")
DAY_ONE_NOON = datetime(2023, 10, 4, 10, tzinfo=UTC)
DAY_TWO_NOON = datetime(2023, 10, 5, 10, tzinfo=UTC)
PLANTS = {"p41": "pretrial", "p47b": "pretrial"}


def _observation(
    kind: ObservationType, value: float, at: datetime, plant_id: str | None = None
) -> Observation:
    return Observation(
        observation_id=f"{plant_id or 'room'}_{kind.value}_{at:%Y%m%d%H}",
        greenhouse_id="gh",
        compartment_id="pretrial",
        plant_id=plant_id,
        timestamp=at,
        observation_type=kind,
        value=value,
        source=SOURCE,
    )


OBSERVATIONS = [
    _observation(ObservationType.AIR_TEMPERATURE_C, 19.0, DAY_ONE_NOON),
    _observation(ObservationType.PLANT_HEIGHT_CM, 20.0, DAY_ONE_NOON, "p41"),
    _observation(ObservationType.AIR_TEMPERATURE_C, 20.0, DAY_TWO_NOON),
    _observation(ObservationType.PLANT_HEIGHT_CM, 25.0, DAY_TWO_NOON, "p41"),
    _observation(ObservationType.RIPE_FRUIT_COUNT, 3.0, DAY_TWO_NOON, "p41"),
]


def test_every_snapshot_carries_each_plant_with_its_latest_readings() -> None:
    states = list(
        reconstruct_checkpoints(
            "gh",
            OBSERVATIONS,
            [],
            every=timedelta(days=1),
            timezone=WUR_LOCAL_TIMEZONE,
            plant_compartments=PLANTS,
        )
    )

    assert [s.timestamp for s in states] == [DAY_ONE_NOON, DAY_TWO_NOON]
    assert [p.plant_id for p in states[0].plant_states] == ["p41", "p47b"]
    day_one = {p.plant_id: p for p in states[0].plant_states}
    day_two = {p.plant_id: p for p in states[1].plant_states}
    assert day_one["p41"].latest_plant_height_cm == 20.0
    assert day_one["p41"].last_measured_at == DAY_ONE_NOON
    assert day_one["p41"].latest_ripe_fruit_count is None
    assert day_two["p41"].latest_plant_height_cm == 25.0
    assert day_two["p41"].latest_ripe_fruit_count == 3
    assert day_two["p41"].compartment_id == "pretrial"
    never_measured = day_two["p47b"]
    assert never_measured.last_measured_at is None
    assert never_measured.latest_plant_height_cm is None
    # weekly manual measurements say nothing about condition
    assert all(p.health == PlantHealth.UNKNOWN for s in states for p in s.plant_states)
    assert states[1].plants_healthy == 0
    # plant readings never land in the compartment's environment
    reference = states[1].compartment("pretrial")
    assert reference is not None
    assert reference.environment.air_temperature_c == 20.0


def test_without_plants_snapshots_carry_no_plant_states() -> None:
    states = list(
        reconstruct_checkpoints(
            "gh", OBSERVATIONS, [], every=timedelta(days=1), timezone=WUR_LOCAL_TIMEZONE
        )
    )

    assert all(s.plant_states == [] for s in states)


def test_loaded_compartment_plants_have_detail_and_history(tmp_path: Path, engine: Engine) -> None:
    measured = Plant(plant_id="p41", variety="cherry", row=9, position_in_row=1)
    unmeasured = Plant(plant_id="p47b", variety="cherry", row=10, position_in_row=2)
    greenhouse = Greenhouse(
        greenhouse_id="gh",
        name="Recorded",
        description="A recorded greenhouse with compartment plants",
        source_type=SourceType.IMPORTED_DATA,
        layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
        plants=[],
        compartments=[
            Compartment(compartment_id="pretrial", name="Pre-trial", plants=[measured, unmeasured])
        ],
        created_at=DAY_ONE_NOON,
    )
    canonical = write_canonical_greenhouse(
        tmp_path / "gh",
        greenhouse=greenhouse,
        observations=OBSERVATIONS,
        events=[],
        dataset_id="test",
        dataset_version=1,
        adapter="test",
        sources=[],
        selection={},
    )

    load_canonical_greenhouse(engine, canonical, checkpoint_timezone=WUR_LOCAL_TIMEZONE)

    service = GreenhouseService(engine)
    history = service.get_plant_history("gh", "p41", up_to=DAY_TWO_NOON)
    assert history is not None
    assert [s.latest_plant_height_cm for s in history] == [20.0, 25.0]
    detail = service.get_plant_detail("gh", "p47b", at=None)
    assert detail is not None
    assert detail.plant == unmeasured
    assert detail.state is not None
    assert detail.state.last_measured_at is None
