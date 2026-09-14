from enum import StrEnum


class SourceType(StrEnum):
    SIMULATION = "SIMULATION"
    REAL_SENSORS = "REAL_SENSORS"
    EXTERNAL_API = "EXTERNAL_API"
    IMPORTED_DATA = "IMPORTED_DATA"


class ObservationType(StrEnum):
    """What an Observation measures. The value doubles as the unit-bearing
    field name on the reconstructed state models (EnvironmentState,
    GreenhouseEnvironmentState), so a new greenhouse-level type is one enum
    member plus one optional field, no mapping table.

    Plant-level readings come from a sensor or vision pass on one plant;
    greenhouse-level readings (plant_id None) describe the compartment's
    climate, its control state, or a manual sample across plants. Recorded
    setpoints are observations of what the controller was asked to do, not
    events: they are continuous 5-minute state, not discrete interventions
    (docs/design/wur_real_data_ingestion_replay_plan.md section 17)."""

    # plant-level
    SOIL_MOISTURE_PCT = "soil_moisture_pct"
    VISIBLE_FRUIT_COUNT = "visible_fruit_count"
    RIPE_FRUIT_COUNT = "ripe_fruit_count"
    ESTIMATED_RIPE_MASS_G = "estimated_ripe_mass_g"
    VISIBLE_HEIGHT_CM = "visible_height_cm"

    # greenhouse-level climate
    AIR_TEMPERATURE_C = "air_temperature_c"
    RELATIVE_HUMIDITY_PCT = "relative_humidity_pct"
    HUMIDITY_DEFICIT_G_M3 = "humidity_deficit_g_m3"
    CO2_PPM = "co2_ppm"
    PAR_UMOL_M2_S = "par_umol_m2_s"
    HEATING_PIPE_TEMPERATURE_C = "heating_pipe_temperature_c"

    # greenhouse-level actuator state
    ENERGY_SCREEN_POSITION_PCT = "energy_screen_position_pct"
    BLACKOUT_SCREEN_POSITION_PCT = "blackout_screen_position_pct"
    WINDOW_POSITION_LEE_PCT = "window_position_lee_pct"
    WINDOW_POSITION_WIND_PCT = "window_position_wind_pct"
    LAMPS_ACTIVATION_PCT = "lamps_activation_pct"

    # greenhouse-level recorded control setpoints
    HEATING_TEMPERATURE_SETPOINT_C = "heating_temperature_setpoint_c"
    VENTILATION_TEMPERATURE_SETPOINT_C = "ventilation_temperature_setpoint_c"
    CO2_SETPOINT_PPM = "co2_setpoint_ppm"
    HUMIDITY_DEFICIT_SETPOINT_G_M3 = "humidity_deficit_setpoint_g_m3"
    LAMPS_ACTIVATION_SETPOINT_PCT = "lamps_activation_setpoint_pct"
    ENERGY_SCREEN_SETPOINT_PCT = "energy_screen_setpoint_pct"
    BLACKOUT_SCREEN_SETPOINT_PCT = "blackout_screen_setpoint_pct"
    IRRIGATION_INTERVAL_SETPOINT_MIN = "irrigation_interval_setpoint_min"
    MINIMUM_PIPE_TEMPERATURE_SETPOINT_C = "minimum_pipe_temperature_setpoint_c"
    MINIMUM_WINDOW_POSITION_LEE_SETPOINT_PCT = "minimum_window_position_lee_setpoint_pct"

    # greenhouse-level effective control values: a setpoint after the
    # controller's own influences ("VIP", value in process) - what it
    # actually tracked, which can differ materially from the setpoint
    HEATING_TEMPERATURE_EFFECTIVE_C = "heating_temperature_effective_c"
    VENTILATION_TEMPERATURE_LEE_EFFECTIVE_C = "ventilation_temperature_lee_effective_c"
    VENTILATION_TEMPERATURE_WIND_EFFECTIVE_C = "ventilation_temperature_wind_effective_c"
    CO2_EFFECTIVE_PPM = "co2_effective_ppm"
    HUMIDITY_DEFICIT_EFFECTIVE_G_M3 = "humidity_deficit_effective_g_m3"
    ENERGY_SCREEN_EFFECTIVE_PCT = "energy_screen_effective_pct"
    BLACKOUT_SCREEN_EFFECTIVE_PCT = "blackout_screen_effective_pct"
    IRRIGATION_INTERVAL_EFFECTIVE_MIN = "irrigation_interval_effective_min"
    MINIMUM_PIPE_TEMPERATURE_EFFECTIVE_C = "minimum_pipe_temperature_effective_c"
    MINIMUM_WINDOW_POSITION_LEE_EFFECTIVE_PCT = "minimum_window_position_lee_effective_pct"

    # greenhouse-level CO2 dosing
    CO2_DOSING_ON = "co2_dosing_on"  # 1 dosing, 0 not
    # minutes dosed since the controller's daily reset (not local midnight)
    CO2_DOSING_MINUTES_SINCE_RESET = "co2_dosing_minutes_since_reset"

    # greenhouse-level increments per m2 over the interval ending at the
    # timestamp; reconstructed as local-day totals (domain/accumulation.py)
    HEATING_ENERGY_INCREMENT_MJ_M2 = "heating_energy_increment_mj_m2"
    LIGHTING_ELECTRICITY_INCREMENT_KWH_M2 = "lighting_electricity_increment_kwh_m2"
    CO2_DOSED_INCREMENT_KG_M2 = "co2_dosed_increment_kg_m2"
    HEATING_COST_INCREMENT_EUR_M2 = "heating_cost_increment_eur_m2"
    LIGHTING_COST_INCREMENT_EUR_M2 = "lighting_cost_increment_eur_m2"
    CO2_COST_INCREMENT_EUR_M2 = "co2_cost_increment_eur_m2"
    FIXED_COST_INCREMENT_EUR_M2 = "fixed_cost_increment_eur_m2"

    # greenhouse-level irrigation
    IRRIGATION_FLOW_DURATION_MIN = "irrigation_flow_duration_min"
    DRAIN_WATER_VOLUME_L_M2 = "drain_water_volume_l_m2"
    DRAIN_EC_DS_M = "drain_ec_ds_m"
    DRAIN_PH = "drain_ph"

    # greenhouse-level manual crop samples (mean over sampled plants)
    SAMPLED_FRUIT_COUNT_PER_PLANT = "sampled_fruit_count_per_plant"
    SAMPLED_FRUIT_FRESH_WEIGHT_G_PER_PLANT = "sampled_fruit_fresh_weight_g_per_plant"

    # compartment crop layout
    PLANT_DENSITY_PER_M2 = "plant_density_per_m2"

    # site weather outside the greenhouse (no compartment)
    OUTSIDE_AIR_TEMPERATURE_C = "outside_air_temperature_c"
    OUTSIDE_RELATIVE_HUMIDITY_PCT = "outside_relative_humidity_pct"
    OUTSIDE_HUMIDITY_DEFICIT_G_M3 = "outside_humidity_deficit_g_m3"
    OUTSIDE_ABSOLUTE_HUMIDITY_G_M3 = "outside_absolute_humidity_g_m3"
    OUTSIDE_GLOBAL_RADIATION_W_M2 = "outside_global_radiation_w_m2"
    # running sum since local midnight
    OUTSIDE_RADIATION_SUM_J_CM2 = "outside_radiation_sum_j_cm2"
    OUTSIDE_WIND_SPEED_M_S = "outside_wind_speed_m_s"
    OUTSIDE_RAIN = "outside_rain"  # 1 raining, 0 dry
    OUTSIDE_PAR_UMOL_M2_S = "outside_par_umol_m2_s"
    OUTSIDE_HEAT_EMISSION_W_M2 = "outside_heat_emission_w_m2"

    # site weather forecast, as known at the observation's timestamp: the
    # forecast total radiation for the current local day, revised during it
    FORECAST_RADIATION_SUM_TODAY_J_CM2 = "forecast_radiation_sum_today_j_cm2"


class EventType(StrEnum):
    WATERING = "WATERING"
    HARVEST = "HARVEST"
    LOWERING = "LOWERING"
    PRUNING = "PRUNING"
    FERTILISATION = "FERTILISATION"
    MANUAL_INSPECTION = "MANUAL_INSPECTION"
    # plants re-spaced to a different density (a whole compartment at once)
    SPACING = "SPACING"


class EventSource(StrEnum):
    HUMAN_REPORTED = "HUMAN_REPORTED"
    ROBOT_CONFIRMED = "ROBOT_CONFIRMED"
    CONTROL_SYSTEM = "CONTROL_SYSTEM"
    INFERRED_FROM_OBSERVATIONS = "INFERRED_FROM_OBSERVATIONS"
    SIMULATION = "SIMULATION"
    RULE_BASED_POLICY = "RULE_BASED_POLICY"
    AGENT = "AGENT"


class FruitStatus(StrEnum):
    GROWING = "GROWING"
    RIPE = "RIPE"
    HARVESTED = "HARVESTED"


class RipenessStage(StrEnum):
    FRUIT_SET = "FRUIT_SET"
    IMMATURE_GREEN = "IMMATURE_GREEN"
    MATURE_GREEN = "MATURE_GREEN"
    TURNING = "TURNING"
    RIPE = "RIPE"
    OVERRIPE = "OVERRIPE"


class TrussStage(StrEnum):
    INITIATED = "INITIATED"
    FRUITING = "FRUITING"
    HARVESTABLE = "HARVESTABLE"
    INACTIVE = "INACTIVE"


class Provenance(StrEnum):
    OBSERVED = "OBSERVED"
    REPORTED = "REPORTED"
    DETERMINISTICALLY_DERIVED = "DETERMINISTICALLY_DERIVED"
    INFERRED = "INFERRED"


class PlantHealth(StrEnum):
    """The plant's own condition, assessed independently of environmental
    readings such as soil moisture (docs/archive/design-history/domain_model_eval_refactor_plan.md
    PR 2) - a plant needing water is not automatically unhealthy. For this
    POC there is one implemented condition signal beyond presence/absence
    of observations: MONITOR when the plant's own visible/fruit readings
    are missing today despite an environment reading coming in (PR 3's
    intelligence.state_reconstruction.assess_plant_condition) - otherwise
    HEALTHY once any observation exists, UNKNOWN before that.
    ACTION_REQUIRED stays available for future condition-specific evidence
    (visual symptoms, sustained deterioration, ...)."""

    HEALTHY = "HEALTHY"
    MONITOR = "MONITOR"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    UNKNOWN = "UNKNOWN"


class SimulationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ManagementPolicyType(StrEnum):
    NONE = "NONE"
    DETERMINISTIC = "DETERMINISTIC"
    AGENTIC = "AGENTIC"


class ActionExecutorType(StrEnum):
    """Who/what actually carries out an accepted action, as opposed to who
    decided it (see management/). Only one member exists today - it makes
    the choice a real, persisted, per-simulation setting rather than a
    hardcoded function call, so a second implementation (a simulated robot
    with different characteristics, later a real one) is a new member plus
    one new class, not a refactor."""

    SIMULATED_OPERATOR = "SIMULATED_OPERATOR"


class RecommendationStatus(StrEnum):
    """Avoid adding statuses with no immediate use
    (docs/archive/design-history/demo_readiness_plan.md section 10):
    approval and execution are synchronous in this pass, so
    there is no persisted APPROVED-but-not-yet-executed state, and nothing
    in the executor can currently fail once validation has passed, so
    there is no FAILED state either."""

    PENDING = "PENDING"
    DISMISSED = "DISMISSED"
    EXECUTED = "EXECUTED"
    REJECTED_BY_VALIDATOR = "REJECTED_BY_VALIDATOR"


class ApprovalSource(StrEnum):
    """Who approved a recommendation - section 7's approved_by. Only one
    member for now (every approval in this pass comes from a human
    operator); a future AUTOMATION_POLICY approver is a new member, not a
    refactor, same pattern as ActionExecutorType."""

    HUMAN = "HUMAN"
