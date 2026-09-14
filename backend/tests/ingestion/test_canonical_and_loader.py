import zipfile
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import openpyxl
from sqlalchemy import Engine

from application.greenhouse_service import GreenhouseService
from application.persistence.observation_repository import ObservationRepository
from domain.enums import ObservationType, SourceType
from ingestion.loader import TimeWindow, load_canonical_greenhouse, reconstruct_checkpoints
from ingestion.manifests import load_manifest
from ingestion.storage.layout import DataDirectory
from ingestion.storage.resolver import ArtifactResolver
from ingestion.wur.agc4_challenge_2024 import TIMESERIES_ARTIFACT, TIMESERIES_MEMBER_PREFIX
from ingestion.wur.agc4_challenge_2024.build import build_greenhouse
from ingestion.wur.agc4_challenge_2024.compartments import GREENHOUSE_ID, compartment
from ingestion.wur.agc4_challenge_2024.timeseries import parse_timeseries
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE
from ingestion.wur.datasets import AGC4_CHALLENGE_2024

C306 = compartment("3.06")


def _csv(days: int = 3) -> str:
    """Two readings a day (noon and 23:55 local) for `days` days from
    2024-09-03, so daily checkpoints have an unambiguous last reading."""
    lines = ["time,compartment/air_temperature,compartment/co2_concentration"]
    for day in range(days):
        date = f"2024-09-{3 + day:02d}"
        lines.append(f"{date} 12:00:00+02:00,{20 + day}.0,{400 + day}")
        lines.append(f"{date} 23:55:00+02:00,{15 + day}.0,")
    return "\n".join(lines) + "\n"


def _harvest_xlsx() -> bytes:
    book = openpyxl.Workbook()
    assert book.active is not None
    book.active.title = "Information"
    final = book.create_sheet("Final Harvest  3.06")
    final.append(["GH #", "plant", "FW tot", "# tot", "# tom green", "fw green", "#tom red"])
    final.append([306, "306-1", 300.0, 40, 10, 50.0, 30])
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _fake_raw_archive(root: Path, csv: str) -> DataDirectory:
    """A fixture shaped like the real timeseries.zip, registered as the
    resolved local copy of the manifest's artifact."""
    manifest = load_manifest(AGC4_CHALLENGE_2024.id)
    artifact = manifest.artifact(TIMESERIES_ARTIFACT)
    data_dir = DataDirectory(root)
    path = data_dir.raw(manifest) / artifact.name
    path.parent.mkdir(parents=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(TIMESERIES_MEMBER_PREFIX + C306.timeseries_member, csv)
        archive.writestr(TIMESERIES_MEMBER_PREFIX + "Harvest.xlsx", _harvest_xlsx())
    # the fixture is not the real artifact: pre-mark it verified
    path.with_name(path.name + ".md5-verified").write_text(artifact.md5 + "\n")
    return data_dir


def test_build_writes_deterministic_canonical_files_with_provenance(tmp_path: Path) -> None:
    data_dir = _fake_raw_archive(tmp_path, _csv())
    resolver = ArtifactResolver(data_dir)

    first = build_greenhouse(data_dir, resolver, [C306])
    first_hashes = first.provenance().content_sha256
    second = build_greenhouse(data_dir, resolver, [C306])

    assert second.provenance().content_sha256 == first_hashes
    provenance = first.provenance()
    assert provenance.dataset_id == AGC4_CHALLENGE_2024.id
    assert provenance.observation_count == 9  # 3 days x (2 temps + 1 co2)
    assert provenance.event_count == 1
    assert [s.member for s in provenance.sources] == [
        TIMESERIES_MEMBER_PREFIX + "timeseries/reference.csv",
        TIMESERIES_MEMBER_PREFIX + "Harvest.xlsx",
    ]
    greenhouse = first.greenhouse()
    assert greenhouse.source_type == SourceType.IMPORTED_DATA
    assert greenhouse.crop == "dwarf_tomato"
    assert greenhouse.layout.kind == "compartment"
    assert greenhouse.plants == []
    assert greenhouse.greenhouse_id == GREENHOUSE_ID
    assert [c.compartment_id for c in greenhouse.compartments] == [
        "3.01",
        "3.02",
        "3.03",
        "3.06",
        "3.07",
        "3.08",
    ]
    assert provenance.selection["compartments"] == ["3.06"]
    assert all(o.compartment_id == "3.06" for o in first.observations())
    assert greenhouse.created_at == datetime(2024, 9, 3, 10, tzinfo=UTC)
    timestamps = [o.timestamp for o in first.observations()]
    assert timestamps == sorted(timestamps)


def test_checkpoints_are_the_last_reading_of_each_local_day_with_carried_values() -> None:
    observations = list(parse_timeseries(_csv(days=2).splitlines(), C306))

    states = list(
        reconstruct_checkpoints(
            GREENHOUSE_ID,
            observations,
            [],
            every=timedelta(days=1),
            timezone=WUR_LOCAL_TIMEZONE,
        )
    )

    assert [s.timestamp for s in states] == [
        datetime(2024, 9, 3, 21, 55, tzinfo=UTC),
        datetime(2024, 9, 4, 21, 55, tzinfo=UTC),
    ]
    # the 23:55 row has no CO2 reading: noon's value carries forward
    reference_day_one = states[0].compartment("3.06")
    reference_day_two = states[1].compartment("3.06")
    assert reference_day_one is not None and reference_day_two is not None
    assert reference_day_one.environment.air_temperature_c == 15.0
    assert reference_day_one.environment.co2_ppm == 400.0
    assert reference_day_two.environment.co2_ppm == 401.0
    assert states[0].environment.air_temperature_c is None
    assert states[0].plant_states == []


def test_load_replaces_records_and_exposes_a_navigable_timeline(
    tmp_path: Path, engine: Engine
) -> None:
    data_dir = _fake_raw_archive(tmp_path, _csv())
    canonical = build_greenhouse(data_dir, ArtifactResolver(data_dir), [C306])

    report = load_canonical_greenhouse(engine, canonical, checkpoint_timezone=WUR_LOCAL_TIMEZONE)
    again = load_canonical_greenhouse(engine, canonical, checkpoint_timezone=WUR_LOCAL_TIMEZONE)

    assert (report.observations, report.events, report.snapshots) == (9, 1, 3)
    assert again == report
    assert len(ObservationRepository(engine).list_for_greenhouse(GREENHOUSE_ID)) == 9

    service = GreenhouseService(engine)
    timeline = service.get_timeline(GREENHOUSE_ID)
    assert timeline is not None
    assert len(timeline.checkpoints) == 3
    assert timeline.current_timestamp == timeline.checkpoints[-1]
    final = service.get_state(GREENHOUSE_ID, at=None)
    assert final is not None
    reference = final.compartment("3.06")
    assert reference is not None and reference.environment.air_temperature_c == 17.0
    assert reference.harvested_total_g == 300.0
    assert final.total_harvested_g == 300.0  # the final harvest, at the recording's end
    middle = service.get_state(GREENHOUSE_ID, at=timeline.checkpoints[1])
    assert middle is not None
    assert middle.total_harvested_g == 0.0
    [item] = service.list_greenhouses()
    assert (item.crop, item.plant_count, item.status) == ("dwarf_tomato", 0, None)


def test_load_window_keeps_only_records_inside_it(tmp_path: Path, engine: Engine) -> None:
    data_dir = _fake_raw_archive(tmp_path, _csv())
    canonical = build_greenhouse(data_dir, ArtifactResolver(data_dir), [C306])

    report = load_canonical_greenhouse(
        engine,
        canonical,
        window=TimeWindow(end=datetime(2024, 9, 4, 23, 59, 59, tzinfo=WUR_LOCAL_TIMEZONE)),
        checkpoint_timezone=WUR_LOCAL_TIMEZONE,
    )

    assert report.snapshots == 2
    assert report.events == 0  # the harvest falls after the window
    observations = ObservationRepository(engine).list_for_greenhouse(GREENHOUSE_ID)
    assert max(o.timestamp for o in observations) == datetime(2024, 9, 4, 21, 55, tzinfo=UTC)
    assert {o.observation_type for o in observations} == {
        ObservationType.AIR_TEMPERATURE_C,
        ObservationType.CO2_PPM,
    }


def test_load_can_be_limited_to_some_compartments(tmp_path: Path, engine: Engine) -> None:
    data_dir = _fake_raw_archive(tmp_path, _csv())
    canonical = build_greenhouse(data_dir, ArtifactResolver(data_dir), [C306])

    nothing = load_canonical_greenhouse(
        engine, canonical, compartment_ids=["3.08"], checkpoint_timezone=WUR_LOCAL_TIMEZONE
    )
    only_306 = load_canonical_greenhouse(
        engine, canonical, compartment_ids=["3.06"], checkpoint_timezone=WUR_LOCAL_TIMEZONE
    )

    assert (nothing.observations, nothing.events, nothing.snapshots) == (0, 0, 0)
    assert (only_306.observations, only_306.events, only_306.snapshots) == (9, 1, 3)


def test_checkpoints_keep_compartment_readings_in_their_compartment() -> None:
    observations = [
        o.model_copy(update={"compartment_id": "3.08"})
        for o in parse_timeseries(_csv(days=2).splitlines(), C306)
    ]

    states = list(
        reconstruct_checkpoints(
            GREENHOUSE_ID,
            observations,
            [],
            every=timedelta(days=1),
            timezone=WUR_LOCAL_TIMEZONE,
        )
    )

    assert len(states) == 2
    assert states[0].environment.air_temperature_c is None
    assert [c.compartment_id for c in states[0].compartments] == ["3.08"]
    reference = states[1].compartment("3.08")
    assert reference is not None
    assert reference.environment.co2_ppm == 401.0
