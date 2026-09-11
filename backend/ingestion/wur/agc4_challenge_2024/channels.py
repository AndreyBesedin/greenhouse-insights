"""Which time-series columns become which ObservationType.

Units are as declared in the dataset's channel_info.json, which already match
the domain's unit conventions (degree_Celsius, percent, ppm, umol/m2/s,
g/m3, minute, L/m2, dS/m) - so no conversion is needed, only selection.

Deliberately not ingested (yet): the *_vip duplicates of every setpoint (the
"value in process" the controller actually tracked - a near-copy of the
setpoint), CO2 actuation/dosage counters, minimum-pipe/-window setpoints,
economics and energy accumulators, and plant density metadata."""

from domain.enums import ObservationType

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
}

TIME_COLUMN = "time"
