from pydantic import TypeAdapter
from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.persistence.schema import sensors
from application.persistence.upsert import upsert
from domain.enums import CaptureModality
from domain.provenance import RecordSource
from domain.sensor import CameraIntrinsics, Sensor

_INTRINSICS = TypeAdapter(dict[CaptureModality, CameraIntrinsics])


class SensorRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_many(self, items: list[Sensor]) -> None:
        """Inserts each sensor, or replaces the one with the same id."""
        if not items:
            return
        with self._engine.begin() as connection:
            for sensor in items:
                upsert(connection, sensors, _sensor_to_row(sensor), key=("sensor_id",))

    def get(self, sensor_id: str) -> Sensor | None:
        statement = select(sensors).where(sensors.c.sensor_id == sensor_id)
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_sensor(row)

    def list_for_greenhouse(
        self, greenhouse_id: str, *, compartment_id: str | None = None
    ) -> list[Sensor]:
        statement = select(sensors).where(sensors.c.greenhouse_id == greenhouse_id)
        if compartment_id is not None:
            statement = statement.where(sensors.c.compartment_id == compartment_id)
        statement = statement.order_by(sensors.c.sensor_id)
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_sensor(row) for row in rows]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(sensors).where(sensors.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _sensor_to_row(sensor: Sensor) -> dict[str, object]:
    ordered = dict(sorted(sensor.intrinsics.items()))
    return {
        "sensor_id": sensor.sensor_id,
        "greenhouse_id": sensor.greenhouse_id,
        "compartment_id": sensor.compartment_id,
        "hardware_model": sensor.hardware_model,
        "device_id": sensor.device_id,
        "intrinsics_json": _INTRINSICS.dump_json(ordered).decode(),
        "nominal_mounting": sensor.nominal_mounting,
        "source_type": sensor.source.type.value,
        "source_id": sensor.source.source_id,
    }


def _row_to_sensor(mapping: RowMapping) -> Sensor:
    return Sensor(
        sensor_id=mapping["sensor_id"],
        greenhouse_id=mapping["greenhouse_id"],
        compartment_id=mapping["compartment_id"],
        hardware_model=mapping["hardware_model"],
        device_id=mapping["device_id"],
        intrinsics=_INTRINSICS.validate_json(mapping["intrinsics_json"]),
        nominal_mounting=mapping["nominal_mounting"],
        source=RecordSource(type=mapping["source_type"], source_id=mapping["source_id"]),
    )
