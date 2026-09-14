"""5-minute CSVs -> canonical Observations (long form: one record per
timestamp per mapped channel with a value).

A compartment's file describes that compartment. The weather and forecast
files describe the site, so their observations name no compartment and are
reconstructed into the greenhouse-level environment."""

import csv
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime

from domain.enums import ObservationType, SourceType
from domain.observation import Observation
from domain.provenance import RecordSource
from ingestion.wur.agc4_challenge_2024 import SOURCE_ID
from ingestion.wur.agc4_challenge_2024.channels import (
    CHANNELS,
    FORECAST_CHANNELS,
    FORECAST_MEMBER,
    TIME_COLUMN,
    WEATHER_CHANNELS,
    WEATHER_MEMBER,
)
from ingestion.wur.agc4_challenge_2024.compartments import GREENHOUSE_ID, Compartment
from ingestion.wur.common.time import parse_offset_timestamp

SOURCE = RecordSource(type=SourceType.IMPORTED_DATA, source_id=SOURCE_ID)
_SITE_SCOPE = "site"


def parse_timeseries(lines: Iterable[str], compartment: Compartment) -> Iterator[Observation]:
    """A compartment's file, in file order (chronological in the source).
    Empty cells are gaps, not zeros: they yield nothing."""
    return _parse(
        lines,
        member=compartment.timeseries_member,
        channels=CHANNELS,
        compartment_id=compartment.compartment_id,
        scope=f"c{compartment.code}",
    )


def parse_weather(lines: Iterable[str]) -> Iterator[Observation]:
    """The site's measured outside weather."""
    return _parse(
        lines,
        member=WEATHER_MEMBER,
        channels=WEATHER_CHANNELS,
        compartment_id=None,
        scope=_SITE_SCOPE,
    )


def parse_forecast(lines: Iterable[str]) -> Iterator[Observation]:
    """The site's weather forecast - only the channels that can be read as
    "known at the row's time" (see channels.py)."""
    return _parse(
        lines,
        member=FORECAST_MEMBER,
        channels=FORECAST_CHANNELS,
        compartment_id=None,
        scope=_SITE_SCOPE,
    )


def observation_id(compartment: Compartment, timestamp: datetime, kind: str) -> str:
    return _observation_id(f"c{compartment.code}", timestamp, kind)


def _parse(
    lines: Iterable[str],
    *,
    member: str,
    channels: Mapping[str, ObservationType],
    compartment_id: str | None,
    scope: str,
) -> Iterator[Observation]:
    reader = csv.DictReader(lines)
    if reader.fieldnames is None or TIME_COLUMN not in reader.fieldnames:
        raise ValueError(f"{member} has no {TIME_COLUMN!r} column")
    mapped = [(column, channels[column]) for column in reader.fieldnames if column in channels]
    if not mapped:
        raise ValueError(f"{member} has none of the expected channels")

    for row in reader:
        timestamp = parse_offset_timestamp(row[TIME_COLUMN])
        for column, observation_type in mapped:
            raw = row.get(column, "")
            if raw is None or raw.strip() == "":
                continue
            yield Observation(
                observation_id=_observation_id(scope, timestamp, observation_type.value),
                greenhouse_id=GREENHOUSE_ID,
                compartment_id=compartment_id,
                plant_id=None,
                timestamp=timestamp,
                observation_type=observation_type,
                value=float(raw),
                source=SOURCE,
            )


def _observation_id(scope: str, timestamp: datetime, kind: str) -> str:
    return f"wur24_{scope}_{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{kind}"
