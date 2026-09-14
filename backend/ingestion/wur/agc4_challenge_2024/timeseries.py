"""A compartment's 5-minute CSV -> canonical Observations (long form: one
record per timestamp per mapped channel with a value)."""

import csv
from collections.abc import Iterable, Iterator
from datetime import datetime

from domain.enums import SourceType
from domain.observation import Observation
from domain.provenance import RecordSource
from ingestion.wur.agc4_challenge_2024 import SOURCE_ID
from ingestion.wur.agc4_challenge_2024.channels import CHANNELS, TIME_COLUMN
from ingestion.wur.agc4_challenge_2024.compartments import Compartment
from ingestion.wur.common.time import parse_offset_timestamp

SOURCE = RecordSource(type=SourceType.IMPORTED_DATA, source_id=SOURCE_ID)


def parse_timeseries(lines: Iterable[str], compartment: Compartment) -> Iterator[Observation]:
    """Yields observations in file order (chronological in the source).
    Empty cells are gaps, not zeros: they yield nothing."""
    reader = csv.DictReader(lines)
    if reader.fieldnames is None or TIME_COLUMN not in reader.fieldnames:
        raise ValueError(f"{compartment.timeseries_member} has no {TIME_COLUMN!r} column")
    mapped = [(column, CHANNELS[column]) for column in reader.fieldnames if column in CHANNELS]
    if not mapped:
        raise ValueError(f"{compartment.timeseries_member} has none of the expected channels")

    for row in reader:
        timestamp = parse_offset_timestamp(row[TIME_COLUMN])
        for column, observation_type in mapped:
            raw = row.get(column, "")
            if raw is None or raw.strip() == "":
                continue
            yield Observation(
                observation_id=observation_id(compartment, timestamp, observation_type.value),
                greenhouse_id=compartment.greenhouse_id,
                plant_id=None,
                timestamp=timestamp,
                observation_type=observation_type,
                value=float(raw),
                source=SOURCE,
            )


def observation_id(compartment: Compartment, timestamp: datetime, kind: str) -> str:
    return f"wur24_c{compartment.code}_{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{kind}"
