from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from application.persistence.media_capture_repository import MediaCaptureRepository
from domain.enums import CaptureModality, SourceType
from domain.media import MediaCapture
from domain.provenance import RecordSource

MORNING = datetime(2024, 10, 2, 2, 6, 14, tzinfo=UTC)


def _capture(
    sensor_id: str,
    at: datetime,
    modality: CaptureModality,
    *,
    greenhouse_id: str = "wur_agc4_2024",
    compartment_id: str | None = "3.06",
) -> MediaCapture:
    stamp = f"{at:%Y%m%dT%H%M%SZ}"
    return MediaCapture(
        capture_id=f"{sensor_id}_{stamp}_{modality.value.lower()}",
        greenhouse_id=greenhouse_id,
        compartment_id=compartment_id,
        sensor_id=sensor_id,
        timestamp=at,
        modality=modality,
        artifact_uri=f"dataset/archive.zip!{sensor_id}/{stamp}_{modality.value.lower()}.png",
        source=RecordSource(type=SourceType.IMPORTED_DATA, source_id="wur_agc4-challenge-2024"),
    )


def test_captures_round_trip_in_chronological_order(engine: Engine) -> None:
    repo = MediaCaptureRepository(engine)
    later = _capture("cam_1", MORNING + timedelta(hours=4), CaptureModality.RGB)
    earlier_depth = _capture("cam_1", MORNING, CaptureModality.DEPTH)
    earlier_rgb = _capture("cam_1", MORNING, CaptureModality.RGB)

    repo.save_many([later, earlier_rgb, earlier_depth])

    assert repo.list_for_greenhouse("wur_agc4_2024") == [earlier_depth, earlier_rgb, later]


def test_listing_filters_by_compartment_sensor_modality_and_instant(engine: Engine) -> None:
    repo = MediaCaptureRepository(engine)
    reference_rgb = _capture("cam_1", MORNING, CaptureModality.RGB)
    reference_depth = _capture("cam_1", MORNING, CaptureModality.DEPTH)
    reference_later = _capture("cam_1", MORNING + timedelta(hours=4), CaptureModality.RGB)
    trigger_rgb = _capture("cam_18", MORNING, CaptureModality.RGB, compartment_id="3.08")
    repo.save_many([reference_rgb, reference_depth, reference_later, trigger_rgb])

    assert repo.list_for_greenhouse("wur_agc4_2024", compartment_id="3.08") == [trigger_rgb]
    assert repo.list_for_greenhouse(
        "wur_agc4_2024", sensor_id="cam_1", modality=CaptureModality.RGB
    ) == [
        reference_rgb,
        reference_later,
    ]
    # the boundary is inclusive, and nothing later leaks in
    assert repo.list_for_greenhouse("wur_agc4_2024", sensor_id="cam_1", up_to=MORNING) == [
        reference_depth,
        reference_rgb,
    ]


def test_delete_for_greenhouse_removes_only_that_greenhouses_captures(engine: Engine) -> None:
    repo = MediaCaptureRepository(engine)
    kept = _capture("cam_19", MORNING, CaptureModality.RGB, greenhouse_id="wur_agc4_2023")
    repo.save_many([_capture("cam_1", MORNING, CaptureModality.RGB), kept])

    repo.delete_for_greenhouse("wur_agc4_2024")

    assert repo.list_for_greenhouse("wur_agc4_2024") == []
    assert repo.list_for_greenhouse("wur_agc4_2023") == [kept]


def test_saving_nothing_is_a_no_op(engine: Engine) -> None:
    repo = MediaCaptureRepository(engine)

    repo.save_many([])

    assert repo.list_for_greenhouse("wur_agc4_2024") == []
