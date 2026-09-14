"""Observation types that are increments, not levels.

Most observations are a level at an instant - a temperature, a setpoint - and
reconstruction keeps the latest one. An increment is an amount over the
interval ending at its timestamp: energy used, CO2 dosed, money spent. The
latest increment means nothing on its own, so reconstruction sums them into a
total for the local day instead. Each increment type names the
GreenhouseEnvironmentState field that holds its daily total.

An increment stamped exactly at local midnight closes the previous day's last
interval, so it counts towards that day."""

from datetime import date, datetime, timedelta, tzinfo

from domain.enums import ObservationType

DAILY_TOTAL_FIELD: dict[ObservationType, str] = {
    ObservationType.HEATING_ENERGY_INCREMENT_MJ_M2: "heating_energy_today_mj_m2",
    ObservationType.LIGHTING_ELECTRICITY_INCREMENT_KWH_M2: "lighting_electricity_today_kwh_m2",
    ObservationType.CO2_DOSED_INCREMENT_KG_M2: "co2_dosed_today_kg_m2",
    ObservationType.HEATING_COST_INCREMENT_EUR_M2: "heating_cost_today_eur_m2",
    ObservationType.LIGHTING_COST_INCREMENT_EUR_M2: "lighting_cost_today_eur_m2",
    ObservationType.CO2_COST_INCREMENT_EUR_M2: "co2_cost_today_eur_m2",
    ObservationType.FIXED_COST_INCREMENT_EUR_M2: "fixed_cost_today_eur_m2",
}


def accounting_day(at: datetime, timezone: tzinfo) -> date:
    """The local day an increment ending at `at` belongs to - and, for a
    snapshot taken at `at`, the day whose totals it may show."""
    return (at - timedelta(microseconds=1)).astimezone(timezone).date()
