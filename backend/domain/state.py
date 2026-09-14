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
    minimum_pipe_temperature_setpoint_c: float | None = None
    minimum_window_position_lee_setpoint_pct: float | None = None

    heating_temperature_effective_c: float | None = None
    ventilation_temperature_lee_effective_c: float | None = None
    ventilation_temperature_wind_effective_c: float | None = None
    co2_effective_ppm: float | None = None
    humidity_deficit_effective_g_m3: float | None = None
    energy_screen_effective_pct: float | None = None
    blackout_screen_effective_pct: float | None = None
    irrigation_interval_effective_min: float | None = None
    minimum_pipe_temperature_effective_c: float | None = None
    minimum_window_position_lee_effective_pct: float | None = None

    co2_dosing_on: float | None = None
    co2_dosing_minutes_since_reset: float | None = None

    # totals for the local day so far, summed from increments
    # (domain/accumulation.py); None when nothing was recorded that day
    heating_energy_today_mj_m2: float | None = None
    lighting_electricity_today_kwh_m2: float | None = None
    co2_dosed_today_kg_m2: float | None = None
    heating_cost_today_eur_m2: float | None = None
    lighting_cost_today_eur_m2: float | None = None
    co2_cost_today_eur_m2: float | None = None
    fixed_cost_today_eur_m2: float | None = None

    irrigation_flow_duration_min: float | None = None
    drain_water_volume_l_m2: float | None = None
    drain_ec_ds_m: float | None = None
    drain_ph: float | None = None

    sampled_fruit_count_per_plant: float | None = None
    sampled_fruit_fresh_weight_g_per_plant: float | None = None

    plant_density_per_m2: float | None = None

    # site weather: only ever set on the greenhouse-level environment
    outside_air_temperature_c: float | None = None
    outside_relative_humidity_pct: float | None = None
    outside_humidity_deficit_g_m3: float | None = None
    outside_absolute_humidity_g_m3: float | None = None
    outside_global_radiation_w_m2: float | None = None
    outside_radiation_sum_j_cm2: float | None = None
    outside_wind_speed_m_s: float | None = None
    outside_rain: float | None = None
    outside_par_umol_m2_s: float | None = None
    outside_heat_emission_w_m2: float | None = None
    forecast_radiation_sum_today_j_cm2: float | None = None

    @classmethod
    def from_latest_values(
        cls,
        latest: dict[ObservationType, float],
        daily_totals: dict[str, float] | None = None,
    ) -> "GreenhouseEnvironmentState":
        known = cls.model_fields
        values: dict[str, float] = {t.value: v for t, v in latest.items() if t.value in known}
        values.update({field: v for field, v in (daily_totals or {}).items() if field in known})
        return cls(**values)


class PlantState(BaseModel):
    plant_id: str
    greenhouse_id: str
    # The compartment the plant stands in, when the greenhouse has them.
    compartment_id: str | None = None
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


class CompartmentState(BaseModel):
    """The reconstructed state of one compartment at the snapshot's instant:
    its own climate / control readings and what has been harvested from it
    as a whole. Its plants are the GreenhouseState's plant_states carrying
    this compartment_id - kept in one flat list so the per-plant views need
    no second lookup."""

    compartment_id: str
    environment: GreenhouseEnvironmentState = GreenhouseEnvironmentState()
    # Harvests recorded for the compartment as a whole (no plant named).
    harvested_total_g: float = 0.0


class GreenhouseState(BaseModel):
    """A reconstructed snapshot of the whole greenhouse at one instant.

    Chronology is the timestamp alone: a simulation-run's day counter is a
    simulation mechanic (simulation/, GreenhouseWorld) and never leaks into
    generic domain records, so the same snapshot shape serves simulated,
    recorded and live greenhouses
    (docs/design/wur_real_data_ingestion_replay_plan.md section 9)."""

    greenhouse_id: str
    timestamp: datetime
    # Readings scoped to the greenhouse as a whole (no compartment).
    environment: GreenhouseEnvironmentState = GreenhouseEnvironmentState()
    # One entry per compartment that has any reconstructed state, in
    # compartment-id order; empty for a compartment-less greenhouse.
    compartments: list[CompartmentState] = []
    plant_states: list[PlantState]
    plants_healthy: int
    plants_monitor: int
    plants_action_required: int
    total_ripe_mass_g: float = 0.0
    # Everything harvested so far: per-plant harvests plus harvests recorded
    # for the greenhouse or a compartment as a whole (a recorded dataset's
    # compartment-level harvest events, which name no individual plant).
    total_harvested_g: float = 0.0

    def compartment(self, compartment_id: str) -> CompartmentState | None:
        return next((c for c in self.compartments if c.compartment_id == compartment_id), None)

    @classmethod
    def aggregate(
        cls,
        *,
        greenhouse_id: str,
        timestamp: datetime,
        plant_states: list[PlantState],
        environment: GreenhouseEnvironmentState | None = None,
        compartments: list[CompartmentState] | None = None,
        greenhouse_harvested_g: float = 0.0,
    ) -> "GreenhouseState":
        compartments = sorted(compartments or [], key=lambda c: c.compartment_id)
        return cls(
            greenhouse_id=greenhouse_id,
            timestamp=timestamp,
            environment=environment or GreenhouseEnvironmentState(),
            compartments=compartments,
            plant_states=plant_states,
            plants_healthy=sum(1 for s in plant_states if s.health == PlantHealth.HEALTHY),
            plants_monitor=sum(1 for s in plant_states if s.health == PlantHealth.MONITOR),
            plants_action_required=sum(
                1 for s in plant_states if s.health == PlantHealth.ACTION_REQUIRED
            ),
            total_ripe_mass_g=sum(s.latest_estimated_ripe_mass_g or 0.0 for s in plant_states),
            total_harvested_g=greenhouse_harvested_g
            + sum(c.harvested_total_g for c in compartments)
            + sum(s.harvested_total_g for s in plant_states),
        )
