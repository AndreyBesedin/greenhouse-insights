from datetime import UTC, datetime, timedelta

import pytest

from domain.accumulation import DAILY_TOTAL_FIELD
from domain.enums import ObservationType
from domain.observation import Observation
from domain.state import CompartmentState, GreenhouseEnvironmentState, GreenhouseState
from ingestion.loader import reconstruct_checkpoints
from ingestion.wur.agc4_challenge_2024.compartments import GREENHOUSE_ID, compartment
from ingestion.wur.agc4_challenge_2024.timeseries import parse_timeseries
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE

# A compartment file's energy and cost columns across local midnight: 1e-10
# is the source's zero, the 00:00 row closes the previous day's last
# interval, and the per-pot cost column is redundant with the per-m2 one.
CSV = """\
time,compartment/air_temperature,energy/energy_use.heating,economics/heating_costs.per_m2,economics/heating_costs.per_pot
2024-10-01 23:50:00+02:00,18.0,0.2,0.005,0.00025
2024-10-01 23:55:00+02:00,18.1,1e-10,1e-10,1e-10
2024-10-02 00:00:00+02:00,18.2,0.3,0.0075,0.000375
2024-10-02 00:05:00+02:00,18.3,0.4,0.01,0.0005
2024-10-02 12:00:00+02:00,21.0,0.6,0.015,0.00075
"""


def _observations(csv: str = CSV) -> list[Observation]:
    return list(parse_timeseries(csv.splitlines(), compartment("3.06")))


def _reference(state: GreenhouseState) -> CompartmentState:
    reference = state.compartment("3.06")
    assert reference is not None
    return reference


def _daily_states(observations: list[Observation]) -> list[GreenhouseState]:
    return list(
        reconstruct_checkpoints(
            GREENHOUSE_ID,
            observations,
            [],
            every=timedelta(days=1),
            timezone=WUR_LOCAL_TIMEZONE,
        )
    )


def test_zero_placeholders_become_zero_and_per_pot_costs_are_skipped() -> None:
    observations = _observations()

    heating = [
        o.value
        for o in observations
        if o.observation_type == ObservationType.HEATING_ENERGY_INCREMENT_MJ_M2
    ]
    assert heating == [0.2, 0.0, 0.3, 0.4, 0.6]
    assert {o.observation_type for o in observations} == {
        ObservationType.AIR_TEMPERATURE_C,
        ObservationType.HEATING_ENERGY_INCREMENT_MJ_M2,
        ObservationType.HEATING_COST_INCREMENT_EUR_M2,
    }


def test_increments_sum_into_local_day_totals_that_restart_after_midnight() -> None:
    states = _daily_states(_observations())

    assert [s.timestamp for s in states] == [
        datetime(2024, 10, 1, 22, 0, tzinfo=UTC),
        datetime(2024, 10, 2, 10, 0, tzinfo=UTC),
    ]
    day_one = _reference(states[0]).environment
    day_two = _reference(states[1]).environment
    # 23:50 + 23:55 (zero) + 00:00, which closes 1 October's last interval
    assert day_one.heating_energy_today_mj_m2 == pytest.approx(0.5)
    assert day_one.heating_cost_today_eur_m2 == pytest.approx(0.0125)
    assert day_two.heating_energy_today_mj_m2 == pytest.approx(1.0)
    assert day_two.heating_cost_today_eur_m2 == pytest.approx(0.025)
    # levels keep working next to totals, and increments are never levels
    assert day_two.air_temperature_c == 21.0
    assert day_two.lighting_electricity_today_kwh_m2 is None


def test_a_day_without_increments_yet_shows_no_total_rather_than_yesterdays() -> None:
    later = CSV + "2024-10-03 00:30:00+02:00,17.5,,,\n"

    last = _reference(_daily_states(_observations(later))[-1]).environment

    assert last.air_temperature_c == 17.5
    assert last.heating_energy_today_mj_m2 is None


def test_every_daily_total_is_a_state_field_and_no_increment_is_one() -> None:
    fields = GreenhouseEnvironmentState.model_fields

    assert all(field in fields for field in DAILY_TOTAL_FIELD.values())
    assert not any(increment.value in fields for increment in DAILY_TOTAL_FIELD)
