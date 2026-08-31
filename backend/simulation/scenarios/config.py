from datetime import date

from pydantic import BaseModel


class ScenarioConfig(BaseModel):
    greenhouse_id: str
    name: str
    description: str
    variety: str
    rows: int
    columns: int
    start_date: date
    duration_days: int
    random_seed: int

    # Environment: bounds the smooth day-to-day drift stays within.
    air_temperature_bounds: tuple[float, float] = (18.0, 32.0)
    humidity_bounds: tuple[float, float] = (45.0, 85.0)

    # Water reservoir / stress.
    initial_water_reservoir_ml: float = 600.0
    water_capacity_ml: float = 1200.0
    watering_amount_ml: float = 700.0
    water_use_ml_per_day_base: float = 80.0
    evaporation_ml_per_day: float = 20.0
    water_stress_threshold_pct: float = 35.0
    watering_trigger_reservoir_pct: float = 40.0

    # Stem / truss growth.
    initial_stem_length_cm: float = 20.0
    stem_growth_cm_per_day_base: float = 2.0
    truss_interval_days: int = 6
    max_trusses: int = 8
    fruits_per_truss_bounds: tuple[int, int] = (3, 6)

    # Fruit growth / ripening.
    target_diameter_mm_bounds: tuple[float, float] = (18.0, 26.0)
    fruit_growth_days_to_target: int = 20
    mass_coefficient_g_per_mm3: float = 0.0012
    ripening_days_bounds: tuple[int, int] = (16, 26)

    # Action thresholds used by the deterministic policy.
    lower_plant_height_threshold_cm: float = 160.0
    lower_plant_amount_cm: float = 40.0
    harvest_ripe_fruit_count_threshold: int = 5

    # Observation noise (standard deviations / detection-error rates).
    soil_moisture_noise_pct: float = 3.0
    air_temperature_noise_c: float = 0.4
    fruit_count_noise_probability: float = 0.1
    ripe_mass_noise_pct: float = 8.0
