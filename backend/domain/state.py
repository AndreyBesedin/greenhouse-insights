from datetime import datetime

from pydantic import BaseModel

from domain.enums import EventType, ObservationType, PlantHealth, Provenance


class EnvironmentState(BaseModel):
    """The reconstructed environment around a plant: soil moisture today,
    with room for future readings (air temperature, humidity, ...). This is
    not plant health - see PlantHealth."""

    soil_moisture_pct: float | None = None


class GreenhouseEnvironmentState(BaseModel):
    """The latest known greenhouse-level readings: climate, actuator
    state, recorded control setpoints and irrigation. Field names are
    ObservationType values, so reconstruction is a lookup, not a mapping.
    Every field is optional - a source only fills what it actually
    measures (the simulator: air temperature; WUR: most of them)."""

    air_temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    humidity_deficit_g_m3: float | None = None
    co2_ppm: float | None = None
    par_umol_m2_s: float | None = None
    heating_pipe_temperature_c: float | None = None

    energy_screen_position_pct: float | None = None
    blackout_screen_position_pct: float | None = None
    window_position_lee_pct: float | None = None
    window_position_wind_pct: float | None = None
    lamps_activation_pct: float | None = None

    heating_temperature_setpoint_c: float | None = None
    ventilation_temperature_setpoint_c: float | None = None
    co2_setpoint_ppm: float | None = None
    humidity_deficit_setpoint_g_m3: float | None = None
    lamps_activation_setpoint_pct: float | None = None
    energy_screen_setpoint_pct: float | None = None
    blackout_screen_setpoint_pct: float | None = None
    irrigation_interval_setpoint_min: float | None = None

    irrigation_flow_duration_min: float | None = None
    drain_water_volume_l_m2: float | None = None
    drain_ec_ds_m: float | None = None
    drain_ph: float | None = None

    sampled_fruit_count_per_plant: float | None = None
    sampled_fruit_fresh_weight_g_per_plant: float | None = None

    @classmethod
    def from_latest_values(
        cls, latest: dict[ObservationType, float]
    ) -> "GreenhouseEnvironmentState":
        known = cls.model_fields
        return cls(**{t.value: v for t, v in latest.items() if t.value in known})


class PlantState(BaseModel):
    plant_id: str
    greenhouse_id: str
    timestamp: datetime
    health: PlantHealth
    latest_soil_moisture_pct: float | None = None
    latest_visible_fruit_count: int | None = None
    latest_ripe_fruit_count: int | None = None
    latest_estimated_ripe_mass_g: float | None = None
    latest_visible_height_cm: float | None = None
    harvested_total_g: float = 0.0
    last_event_type: EventType | None = None
    last_event_timestamp: datetime | None = None
    provenance: Provenance = Provenance.DETERMINISTICALLY_DERIVED


class GreenhouseState(BaseModel):
    """A reconstructed snapshot of the whole greenhouse at one instant.

    Chronology is the timestamp alone: a simulation-run's day counter is a
    simulation mechanic (simulation/, GreenhouseWorld) and never leaks into
    generic domain records, so the same snapshot shape serves simulated,
    recorded and live greenhouses
    (docs/design/wur_real_data_ingestion_replay_plan.md section 9)."""

    greenhouse_id: str
    timestamp: datetime
    environment: GreenhouseEnvironmentState = GreenhouseEnvironmentState()
    plant_states: list[PlantState]
    plants_healthy: int
    plants_monitor: int
    plants_action_required: int
    total_ripe_mass_g: float = 0.0
    # Everything harvested so far: per-plant harvests plus harvests recorded
    # for the greenhouse as a whole (a recorded dataset's compartment-level
    # harvest events, which name no individual plant).
    total_harvested_g: float = 0.0

    @classmethod
    def aggregate(
        cls,
        *,
        greenhouse_id: str,
        timestamp: datetime,
        plant_states: list[PlantState],
        environment: GreenhouseEnvironmentState | None = None,
        greenhouse_harvested_g: float = 0.0,
    ) -> "GreenhouseState":
        return cls(
            greenhouse_id=greenhouse_id,
            timestamp=timestamp,
            environment=environment or GreenhouseEnvironmentState(),
            plant_states=plant_states,
            plants_healthy=sum(1 for s in plant_states if s.health == PlantHealth.HEALTHY),
            plants_monitor=sum(1 for s in plant_states if s.health == PlantHealth.MONITOR),
            plants_action_required=sum(
                1 for s in plant_states if s.health == PlantHealth.ACTION_REQUIRED
            ),
            total_ripe_mass_g=sum(s.latest_estimated_ripe_mass_g or 0.0 for s in plant_states),
            total_harvested_g=greenhouse_harvested_g
            + sum(s.harvested_total_g for s in plant_states),
        )
