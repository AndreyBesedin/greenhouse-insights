"""A recorded image, by reference: which sensor took it, when, in what
modality, and where its bytes live.

Pixels never enter the application database. Perception reads the artifact
through the ingestion storage layer and emits derived Observations that
point back to the capture they came from
(docs/design/wur_real_data_ingestion_replay_plan.md section 8,
docs/design/wur_execution_plan.md F1)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from domain.enums import CaptureModality
from domain.provenance import RecordSource


class MediaCapture(BaseModel):
    model_config = ConfigDict(frozen=True)

    capture_id: str
    greenhouse_id: str
    # The compartment the sensor looks at, when the greenhouse has them.
    compartment_id: str | None = None
    sensor_id: str
    timestamp: datetime
    modality: CaptureModality
    # Where the bytes are: "<dataset id>/<artifact name>!<member path>" for a
    # member of a source archive. The storage layer resolves it; the domain
    # never opens it.
    artifact_uri: str
    source: RecordSource

    @field_validator("timestamp")
    @classmethod
    def _timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("a capture timestamp must be timezone-aware")
        return value
