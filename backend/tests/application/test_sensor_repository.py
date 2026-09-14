from sqlalchemy import Engine

from application.persistence.sensor_repository import SensorRepository
from domain.enums import CaptureModality, SourceType
from domain.provenance import RecordSource
from domain.sensor import CameraIntrinsics, Sensor

COLOUR = CameraIntrinsics(
    width=3840,
    height=2160,
    fx=3115.85,
    fy=3115.85,
    ppx=1866.7,
    ppy=1109.56,
    distortion=(13.17, -143.7, 0.0),
)
MONO = CameraIntrinsics(width=1280, height=720, fx=810.46, fy=810.46, ppx=643.49, ppy=398.1)
SOURCE = RecordSource(type=SourceType.IMPORTED_DATA, source_id="wur_agc4-challenge-2024")


def _camera(
    sensor_id: str, compartment_id: str | None, *, device_id: str | None = "serial"
) -> Sensor:
    return Sensor(
        sensor_id=sensor_id,
        greenhouse_id="wur_agc4_2024",
        compartment_id=compartment_id,
        hardware_model="Oak-D S2 POE",
        device_id=device_id,
        intrinsics={
            CaptureModality.RGB: COLOUR,
            CaptureModality.DEPTH: COLOUR,
            CaptureModality.INFRARED_LEFT: MONO,
        },
        nominal_mounting="About 1.5 m above the growing crop, facing downwards.",
        source=SOURCE,
    )


def test_sensors_round_trip_with_their_intrinsics(engine: Engine) -> None:
    repo = SensorRepository(engine)
    camera = _camera("wur24_cam_1", "3.06", device_id=None)

    repo.save_many([camera])

    assert repo.get("wur24_cam_1") == camera
    assert repo.get("unknown") is None


def test_saving_a_sensor_again_replaces_it(engine: Engine) -> None:
    repo = SensorRepository(engine)
    repo.save_many([_camera("wur24_cam_1", "3.06")])
    recalibrated = _camera("wur24_cam_1", "3.06").model_copy(
        update={"intrinsics": {CaptureModality.RGB: MONO}}
    )

    repo.save_many([recalibrated])

    assert repo.get("wur24_cam_1") == recalibrated


def test_listing_filters_by_compartment_in_sensor_id_order(engine: Engine) -> None:
    repo = SensorRepository(engine)
    trigger, reference = _camera("wur24_cam_18", "3.08"), _camera("wur24_cam_1", "3.06")
    repo.save_many([trigger, reference])

    assert repo.list_for_greenhouse("wur_agc4_2024") == [reference, trigger]
    assert repo.list_for_greenhouse("wur_agc4_2024", compartment_id="3.08") == [trigger]


def test_delete_for_greenhouse_removes_its_sensors(engine: Engine) -> None:
    repo = SensorRepository(engine)
    repo.save_many([_camera("wur24_cam_1", "3.06")])

    repo.delete_for_greenhouse("wur_agc4_2024")

    assert repo.list_for_greenhouse("wur_agc4_2024") == []
