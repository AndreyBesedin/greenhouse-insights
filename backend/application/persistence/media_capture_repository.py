from datetime import datetime

from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import RowMapping

from application.persistence.schema import media_captures
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp
from domain.enums import CaptureModality
from domain.media import MediaCapture
from domain.provenance import RecordSource


class MediaCaptureRepository:
    """Capture metadata only - the images themselves stay in their source
    artifacts."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_many(self, items: list[MediaCapture]) -> None:
        if not items:
            return
        rows = [_capture_to_row(item) for item in items]
        with self._engine.begin() as connection:
            connection.execute(media_captures.insert(), rows)

    def list_for_greenhouse(
        self,
        greenhouse_id: str,
        *,
        compartment_id: str | None = None,
        sensor_id: str | None = None,
        modality: CaptureModality | None = None,
        up_to: datetime | None = None,
    ) -> list[MediaCapture]:
        """Captures in chronological order (ties by capture id), optionally
        only those taken at or before `up_to` - the same temporal-honesty
        boundary observations have."""
        statement = select(media_captures).where(media_captures.c.greenhouse_id == greenhouse_id)
        if compartment_id is not None:
            statement = statement.where(media_captures.c.compartment_id == compartment_id)
        if sensor_id is not None:
            statement = statement.where(media_captures.c.sensor_id == sensor_id)
        if modality is not None:
            statement = statement.where(media_captures.c.modality == modality.value)
        if up_to is not None:
            statement = statement.where(media_captures.c.timestamp <= to_db_timestamp(up_to))
        statement = statement.order_by(media_captures.c.timestamp, media_captures.c.capture_id)

        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_capture(row) for row in rows]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(media_captures).where(media_captures.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _capture_to_row(capture: MediaCapture) -> dict[str, object]:
    return {
        "capture_id": capture.capture_id,
        "greenhouse_id": capture.greenhouse_id,
        "compartment_id": capture.compartment_id,
        "sensor_id": capture.sensor_id,
        "timestamp": to_db_timestamp(capture.timestamp),
        "modality": capture.modality.value,
        "artifact_uri": capture.artifact_uri,
        "source_type": capture.source.type.value,
        "source_id": capture.source.source_id,
    }


def _row_to_capture(mapping: RowMapping) -> MediaCapture:
    return MediaCapture(
        capture_id=mapping["capture_id"],
        greenhouse_id=mapping["greenhouse_id"],
        compartment_id=mapping["compartment_id"],
        sensor_id=mapping["sensor_id"],
        timestamp=from_db_timestamp(mapping["timestamp"]),
        modality=mapping["modality"],
        artifact_uri=mapping["artifact_uri"],
        source=RecordSource(type=mapping["source_type"], source_id=mapping["source_id"]),
    )
