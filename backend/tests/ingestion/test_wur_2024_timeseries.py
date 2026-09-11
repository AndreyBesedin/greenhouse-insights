from datetime import UTC, datetime

import pytest

from domain.enums import ObservationType, SourceType
from ingestion.wur.agc4_challenge_2024.compartments import COMPARTMENTS, compartment
from ingestion.wur.agc4_challenge_2024.timeseries import parse_timeseries
from ingestion.wur.common.time import excel_serial_to_utc, local_noon, parse_offset_timestamp

# A trimmed slice of reference.csv's shape: the time column, a few mapped
# channels, one unmapped economics column, gaps, and the DST changeover.
CSV = """\
time,compartment/air_temperature,compartment/relative_humidity,compartment/heating_temperature_setpoint,economics/fixed_costs.per_m2
2024-10-27 02:55:00+02:00,19.5,81.0,18.0,0.01
2024-10-27 02:00:00+01:00,19.4,,18.0,0.01
2024-10-27 02:05:00+01:00,,80.5,18.5,0.01
"""


def test_parses_mapped_channels_into_utc_greenhouse_level_observations() -> None:
    observations = list(parse_timeseries(CSV.splitlines(), compartment("3.06")))

    first = observations[0]
    assert first.greenhouse_id == "wur_agc4_2024_c306"
    assert first.plant_id is None
    assert first.timestamp == datetime(2024, 10, 27, 0, 55, tzinfo=UTC)
    assert first.observation_type == ObservationType.AIR_TEMPERATURE_C
    assert first.value == 19.5
    assert first.source.type == SourceType.IMPORTED_DATA
    assert first.source.source_id == "wur_agc4-challenge-2024"


def test_empty_cells_are_gaps_and_unmapped_columns_are_ignored() -> None:
    observations = list(parse_timeseries(CSV.splitlines(), compartment("3.06")))

    by_row: dict[datetime, set[ObservationType]] = {}
    for obs in observations:
        by_row.setdefault(obs.timestamp, set()).add(obs.observation_type)
    assert by_row[datetime(2024, 10, 27, 1, 0, tzinfo=UTC)] == {
        ObservationType.AIR_TEMPERATURE_C,
        ObservationType.HEATING_TEMPERATURE_SETPOINT_C,
    }
    assert by_row[datetime(2024, 10, 27, 1, 5, tzinfo=UTC)] == {
        ObservationType.RELATIVE_HUMIDITY_PCT,
        ObservationType.HEATING_TEMPERATURE_SETPOINT_C,
    }
    assert all(o.observation_type != ObservationType.SOIL_MOISTURE_PCT for o in observations)


def test_the_dst_changeover_keeps_utc_order_and_unique_ids() -> None:
    observations = list(parse_timeseries(CSV.splitlines(), compartment("3.06")))

    timestamps = [o.timestamp for o in observations]
    assert timestamps == sorted(timestamps)
    assert len({o.observation_id for o in observations}) == len(observations)


def test_a_file_without_the_time_column_is_refused() -> None:
    with pytest.raises(ValueError, match="time"):
        list(parse_timeseries(["a,b", "1,2"], compartment("3.06")))


def test_every_compartment_has_a_distinct_greenhouse_identity() -> None:
    ids = {c.greenhouse_id for c in COMPARTMENTS.values()}
    assert len(ids) == 6
    assert compartment("3.01").code == "301"
    with pytest.raises(KeyError):
        compartment("9.99")


def test_timestamp_helpers_normalise_dutch_local_time_to_utc() -> None:
    assert parse_offset_timestamp("2024-09-03 00:00:00+02:00") == datetime(
        2024, 9, 2, 22, 0, tzinfo=UTC
    )
    with pytest.raises(ValueError):
        parse_offset_timestamp("2024-09-03 00:00:00")
    # local noon is 10:00Z in summer time and 11:00Z in winter time
    assert local_noon(datetime(2024, 10, 7).date()) == datetime(2024, 10, 7, 10, tzinfo=UTC)
    assert local_noon(datetime(2024, 11, 5).date()) == datetime(2024, 11, 5, 11, tzinfo=UTC)
    # Excel serial 45174.5 is 2023-09-05 12:00 local (CEST)
    assert excel_serial_to_utc(45174.5) == datetime(2023, 9, 5, 10, tzinfo=UTC)
