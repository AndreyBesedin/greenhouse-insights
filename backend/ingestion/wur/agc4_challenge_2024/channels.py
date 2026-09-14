"""Which time-series columns become which ObservationType.

Units are as declared in the dataset's channel_info.json, which already match
the domain's unit conventions (degree_Celsius, percent, ppm, umol/m2/s,
g/m3, minute, L/m2, dS/m, W/m2, J/cm2, m/s) - so no conversion is needed,
only selection.

Not ingested yet from the compartment files (docs/design/wur_execution_plan.md
steps E2c-E2e): the `*_vip` effective setpoints (which differ from their
setpoints far more than the name suggests), CO2 dosing state and counters,
minimum pipe / window setpoints, energy and cost increments, and per-sensor
extras. `dwarf_tomato/harvest_date` is read separately, as the final-harvest
instant (timeseries.final_harvest_timestamp); `dwarf_tomato/pot_area` is
skipped as the exact reciprocal of plant density.

Deliberately not ingested from the site files, both for temporal honesty
(docs/design/wur_real_data_ingestion_replay_plan.md sections 10-11), as
measured on 2026-09-14:

- `weather/wind_direction.registration` holds eight bit-flag values (1, 2, 4
  ... 128), not the degrees its channel_info claims, and nothing in the
  dataset says which flag is which compass sector. Unknown stays unknown.
- The hourly `weather_forecast/*` fields (temperature, humidity, radiation,
  wind, cloudiness) are indexed by the time the forecast is valid for, not
  when it was issued: forecast temperature at t tracks measured temperature
  at t to 0.66 degC MAE, closer than at any lag. With no issue time, a replay
  at T cannot know which of them existed at T. Only the daily radiation-sum
  forecast is ingested: it is a running value for the current local day,
  revised during the day and converging on that day's measured total, so the
  row at t is read as "the forecast as known at t"."""

from domain.enums import ObservationType

TIME_COLUMN = "time"
WEATHER_MEMBER = "timeseries/weather.csv"
FORECAST_MEMBER = "timeseries/weather_forecast.csv"
# The day of year of a compartment's final harvest, written once, on the
# harvest day's last row of that compartment's file.
HARVEST_DAY_COLUMN = "dwarf_tomato/harvest_date"

CHANNELS: dict[str, ObservationType] = {
    # measured climate
    "compartment/air_temperature": ObservationType.AIR_TEMPERATURE_C,
    "compartment/relative_humidity": ObservationType.RELATIVE_HUMIDITY_PCT,
    "compartment/humidity_deficit": ObservationType.HUMIDITY_DEFICIT_G_M3,
    "compartment/co2_concentration": ObservationType.CO2_PPM,
    "compartment/par": ObservationType.PAR_UMOL_M2_S,
    "compartment/heating_lower_circuit/pipe_temperature": (
        ObservationType.HEATING_PIPE_TEMPERATURE_C
    ),
    # actuator state
    "compartment/screen_energy/screen_position": ObservationType.ENERGY_SCREEN_POSITION_PCT,
    "compartment/screen_blackout/screen_position": ObservationType.BLACKOUT_SCREEN_POSITION_PCT,
    "compartment/window_position_lee_side": ObservationType.WINDOW_POSITION_LEE_PCT,
    "compartment/window_position_wind_side": ObservationType.WINDOW_POSITION_WIND_PCT,
    "compartment/lamps_activation_percentage": ObservationType.LAMPS_ACTIVATION_PCT,
    # recorded control setpoints
    "compartment/heating_temperature_setpoint": ObservationType.HEATING_TEMPERATURE_SETPOINT_C,
    "compartment/ventilation_temperature_setpoint": (
        ObservationType.VENTILATION_TEMPERATURE_SETPOINT_C
    ),
    "compartment/co2_concentration_setpoint": ObservationType.CO2_SETPOINT_PPM,
    "compartment/humidity_deficit_setpoint": ObservationType.HUMIDITY_DEFICIT_SETPOINT_G_M3,
    "compartment/lamps_activation_percentage_setpoint": (
        ObservationType.LAMPS_ACTIVATION_SETPOINT_PCT
    ),
    "compartment/screen_energy/screen_position_setpoint": (
        ObservationType.ENERGY_SCREEN_SETPOINT_PCT
    ),
    "compartment/screen_blackout/screen_position_setpoint": (
        ObservationType.BLACKOUT_SCREEN_SETPOINT_PCT
    ),
    "compartment/water_supply/water_supply_interval_setpoint": (
        ObservationType.IRRIGATION_INTERVAL_SETPOINT_MIN
    ),
    # irrigation
    "compartment/water_supply/water_flow_duration": ObservationType.IRRIGATION_FLOW_DURATION_MIN,
    "compartment/water_drain/water_volume": ObservationType.DRAIN_WATER_VOLUME_L_M2,
    "compartment/water_drain/ec": ObservationType.DRAIN_EC_DS_M,
    "compartment/water_drain/ph": ObservationType.DRAIN_PH,
    # crop layout: recorded only on the day a density takes effect
    "dwarf_tomato/plant_density": ObservationType.PLANT_DENSITY_PER_M2,
}

WEATHER_CHANNELS: dict[str, ObservationType] = {
    "weather/air_temperature.outside": ObservationType.OUTSIDE_AIR_TEMPERATURE_C,
    "weather/relative_humidity.outside": ObservationType.OUTSIDE_RELATIVE_HUMIDITY_PCT,
    "weather/humidity_deficit": ObservationType.OUTSIDE_HUMIDITY_DEFICIT_G_M3,
    "weather/air_absolute_humidity_content.outside": (
        ObservationType.OUTSIDE_ABSOLUTE_HUMIDITY_G_M3
    ),
    "weather/radiation_global": ObservationType.OUTSIDE_GLOBAL_RADIATION_W_M2,
    "weather/radiation_sum": ObservationType.OUTSIDE_RADIATION_SUM_J_CM2,
    "weather/wind_speed": ObservationType.OUTSIDE_WIND_SPEED_M_S,
    "weather/rain_state": ObservationType.OUTSIDE_RAIN,
    "weather/par.outside": ObservationType.OUTSIDE_PAR_UMOL_M2_S,
    "weather/heat_emission": ObservationType.OUTSIDE_HEAT_EMISSION_W_M2,
}

FORECAST_CHANNELS: dict[str, ObservationType] = {
    "weather_forecast/radiation_sum": ObservationType.FORECAST_RADIATION_SUM_TODAY_J_CM2,
}
