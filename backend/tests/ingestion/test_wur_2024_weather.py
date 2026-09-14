from datetime import UTC, datetime, timedelta

from domain.enums import ObservationType
from ingestion.loader import reconstruct_checkpoints
from ingestion.wur.agc4_challenge_2024.compartments import GREENHOUSE_ID, compartment
from ingestion.wur.agc4_challenge_2024.timeseries import (
    parse_forecast,
    parse_timeseries,
    parse_weather,
)
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE

# The real weather.csv's shape, trimmed: mapped channels plus the wind
# direction bit-flag column that must not be ingested.
WEATHER = """\
time,weather/air_temperature.outside,weather/radiation_sum,weather/wind_direction.registration,weather/rain_state
2024-09-03 12:00:00+02:00,21.5,640.0,8.0,0.0
2024-09-03 12:05:00+02:00,21.7,652.0,16.0,1.0
"""

# The real weather_forecast.csv's shape: a running daily radiation-sum
# forecast on every row, and hourly valid-time fields that must be skipped.
FORECAST = """\
time,weather_forecast/air_temperature.outside,weather_forecast/radiation_sum,weather_forecast/degree_of_cloudiness
2024-09-03 12:00:00+02:00,21.9,1099.0,3.0
2024-09-03 12:05:00+02:00,,1101.0,
"""


def test_weather_becomes_site_level_observations_without_wind_direction() -> None:
    observations = list(parse_weather(WEATHER.splitlines()))

    assert {o.observation_type for o in observations} == {
        ObservationType.OUTSIDE_AIR_TEMPERATURE_C,
        ObservationType.OUTSIDE_RADIATION_SUM_J_CM2,
        ObservationType.OUTSIDE_RAIN,
    }
    assert len(observations) == 6
    assert all(o.greenhouse_id == GREENHOUSE_ID for o in observations)
    assert all(o.compartment_id is None and o.plant_id is None for o in observations)
    first = observations[0]
    assert first.timestamp == datetime(2024, 9, 3, 10, tzinfo=UTC)
    assert first.observation_id == "wur24_site_20240903T100000Z_outside_air_temperature_c"
    assert len({o.observation_id for o in observations}) == 6


def test_only_the_running_radiation_sum_forecast_is_ingested() -> None:
    observations = list(parse_forecast(FORECAST.splitlines()))

    assert [(o.timestamp, o.observation_type, o.value) for o in observations] == [
        (
            datetime(2024, 9, 3, 10, tzinfo=UTC),
            ObservationType.FORECAST_RADIATION_SUM_TODAY_J_CM2,
            1099.0,
        ),
        (
            datetime(2024, 9, 3, 10, 5, tzinfo=UTC),
            ObservationType.FORECAST_RADIATION_SUM_TODAY_J_CM2,
            1101.0,
        ),
    ]
    assert all(o.compartment_id is None for o in observations)


def test_site_weather_reconstructs_into_the_greenhouse_environment_only() -> None:
    compartment_rows = "time,compartment/air_temperature\n2024-09-03 12:00:00+02:00,19.0\n"
    observations = sorted(
        [
            *parse_timeseries(compartment_rows.splitlines(), compartment("3.06")),
            *parse_weather(WEATHER.splitlines()),
            *parse_forecast(FORECAST.splitlines()),
        ],
        key=lambda o: o.timestamp,
    )

    [state] = reconstruct_checkpoints(
        GREENHOUSE_ID, observations, [], every=timedelta(days=1), timezone=WUR_LOCAL_TIMEZONE
    )

    assert state.environment.outside_air_temperature_c == 21.7
    assert state.environment.outside_rain == 1.0
    assert state.environment.forecast_radiation_sum_today_j_cm2 == 1101.0
    assert state.environment.air_temperature_c is None
    reference = state.compartment("3.06")
    assert reference is not None
    assert reference.environment.air_temperature_c == 19.0
    assert reference.environment.outside_air_temperature_c is None
