# Greenhouse Simulation Engine — Design Document

## 1. Purpose

This document defines the design of the **logical greenhouse simulation engine** used by the Greenhouse Intelligence POC.

The simulator is not a playback of hand-written scenarios. It is a **generative world model**: a simplified hidden representation of a greenhouse evolves one simulated day at a time according to deterministic and probabilistic rules. Sensors and a hypothetical computer-vision system then produce noisy observations from that hidden state.

The main objective is to produce coherent longitudinal greenhouse data that can later be consumed by the intelligence platform exactly as real greenhouse observations would be.

The simulator should be simple enough to understand and modify, but rich enough to generate meaningful temporal relationships such as:

- plants growing over time;
- new trusses and fruits appearing;
- fruits increasing in size and ripening;
- watering affecting substrate moisture;
- hot days increasing water demand;
- harvesting causing fruits to disappear from later observations;
- lowering a vine changing its management state;
- noisy observations differing slightly from ground truth.

The simulator is therefore an **input generator for the platform**, not the intelligence layer itself.

---

## 2. Core Principle: Hidden World vs Observed World

The simulator must maintain a strict separation between:

```text
HIDDEN WORLD STATE
    ↓
DAILY DYNAMICS
    ↓
OPERATOR / AUTOMATION ACTIONS
    ↓
UPDATED HIDDEN WORLD STATE
    ↓
OBSERVATION MODEL
    ↓
PLATFORM INPUT
```

The hidden world is the simulator's ground truth.

The platform should never consume this state directly.

Instead, the simulator generates the same categories of information that a future physical greenhouse could produce:

- environmental sensor observations;
- soil-moisture observations;
- structured outputs from a future vision pipeline;
- reported operational events.

This separation allows the simulator to later test whether the intelligence layer can correctly reconstruct reality from incomplete or noisy evidence.

---

## 3. Time Model

The initial simulator works at **daily resolution**.

One simulation step represents one day.

```text
Day 0
  ↓
Day 1
  ↓
Day 2
  ↓
...
  ↓
Day N
```

This is intentionally coarse.

The POC does not need second-by-second irrigation, climate control or biological processes.

Internally, some daily quantities may represent aggregated values, for example:

- average temperature;
- maximum temperature;
- hours above a threshold;
- total irrigation volume;
- estimated evapotranspiration.

The architecture should not make higher-frequency simulation impossible later, but no effort should be spent supporting it in the first version.

---

## 4. Simulation Determinism

Every simulation run must be reproducible from a random seed.

Example:

```text
seed = 42
```

Running the same simulation configuration with the same seed should produce the same hidden world and the same noisy observations.

This is essential for:

- debugging;
- evaluation;
- regression testing;
- demonstrations;
- comparing reasoning implementations.

All stochastic behaviour should therefore use an explicitly controlled random-number generator.

---

## 5. Main Domain Hierarchy

The hidden simulation world is organized approximately as:

```text
SimulationWorld
    │
    └── Greenhouse
          ├── Environment
          ├── ClimateField
          └── Plants[]
                ├── Root / substrate state
                ├── Stem / management state
                └── Trusses[]
                      └── Fruits[]
```

The first POC greenhouse contains cherry-tomato or vine-tomato plants, but the simulator should avoid unnecessary assumptions that make other crops impossible later.

---

# 6. Greenhouse Model

A greenhouse is a spatial container for plants and environmental conditions.

Conceptual structure:

```python
Greenhouse
    id
    name
    width_m
    length_m
    plants
    heating_sources
    environment_state
```

Example:

```json
{
  "id": "greenhouse_001",
  "name": "Simulation Greenhouse 001",
  "width_m": 8.0,
  "length_m": 20.0
}
```

The exact dimensions are configuration values and should not be hard-coded into biological logic.

---

## 7. Plant Placement

Plants have stable positions in the greenhouse.

At minimum:

```text
plant_id
row
position_in_row
x
 y
```

Example:

```json
{
  "plant_id": "plant_017",
  "row": 2,
  "position_in_row": 7,
  "x": 5.8,
  "y": 8.2
}
```

For the main POC:

```text
40 plants
4 rows × 10 plants
```

Positions serve two purposes:

1. rendering the greenhouse dashboard;
2. allowing environmental values to vary spatially.

The simulator does **not** model detailed plant geometry.

---

# 8. Plant Model

The plant represents the hidden biological and operational state of one indeterminate vine tomato.

Conceptual fields:

```python
Plant
    id
    variety
    position

    age_days
    physiological_age

    stem_length_cm
    lowered_length_cm

    development_stage

    substrate_state
    water_stress
    heat_stress
    health_state

    trusses

    cumulative_harvest_g
    cumulative_fruit_count_harvested

    last_watered_at
    last_lowered_at
    last_harvest_at
```

The plant should represent **meaningful operational state**, not a geometrically accurate tomato vine.

---

## 9. Plant Development Stage

An initial enum could be:

```text
VEGETATIVE
FLOWERING
FRUITING
MATURE
DECLINING
```

For the first simulation, most interesting behaviour happens during `FRUITING` and `MATURE`.

Development stage can be derived primarily from plant age and the presence/state of trusses rather than managed as an independent random variable.

---

# 10. Stem Growth

Indeterminate greenhouse tomatoes continue growing vertically throughout production.

The simulator should track:

```text
stem_length_cm
lowered_length_cm
```

Daily stem growth can be represented as:

```text
daily_stem_growth
    = base_growth_rate
    × temperature_factor
    × water_factor
    × plant_variation
```

For example:

```python
plant.stem_length_cm += daily_stem_growth_cm
```

The exact constants are **tunable simulation parameters**, not claims of biological accuracy.

---

# 11. Plant Lowering

Commercial indeterminate tomatoes are periodically lowered as the stem continues growing.

The POC models lowering as an operational action rather than detailed physical geometry.

Example action:

```python
LowerPlant(
    plant_id="plant_017",
    lowered_by_cm=35,
)
```

Its effect is primarily:

```python
plant.lowered_length_cm += lowered_by_cm
plant.last_lowered_at = current_day
```

A useful derived quantity is:

```text
effective_vertical_height
    = stem_length_cm - lowered_length_cm
```

No spiral geometry, clips, strings or physical collision model is required.

---

# 12. Truss Model

Fruit should not appear independently at arbitrary positions.

Tomato production is represented through **trusses**.

Conceptual structure:

```python
Truss
    id
    plant_id
    index

    age_days
    physiological_age

    status

    flowering_progress
    fruit_set_complete

    fruits
```

Possible status values:

```text
FORMING
FLOWERING
FRUIT_SETTING
FRUITING
HARVESTABLE
HARVESTED
INACTIVE
```

A plant creates new trusses as it accumulates physiological development.

---

# 13. Truss Appearance

New trusses should be initiated according to **effective development**, not purely random daily spawning.

Conceptually:

```text
physiological_age += temperature_factor × stress_factor
```

When enough development has accumulated since the previous truss:

```text
create new truss
```

Each plant can have a small individual multiplier so that all 40 plants are not synchronized perfectly.

For example:

```text
truss_interval_effective_days
    ~ Normal(base_interval, variation)
```

Exact parameters should be easy to tune in configuration.

---

# 14. Fruit Model

Individual fruits exist in hidden world state.

Conceptual fields:

```python
Fruit
    id
    plant_id
    truss_id

    age_days
    physiological_age

    status
    ripeness_stage

    diameter_mm
    mass_g

    target_diameter_mm
    target_mass_g

    development_speed

    set_day
    harvested_day
```

Fruit IDs are **ground-truth simulation IDs**.

A future simulated computer-vision tracker may expose different observation track IDs.

---

# 15. Fruit Lifecycle

A simple lifecycle is sufficient:

```text
FLOWER
   ↓
FRUIT_SET
   ↓
IMMATURE_GREEN
   ↓
MATURE_GREEN
   ↓
BREAKER
   ↓
TURNING
   ↓
RED
   ↓
OVERRIPE
   ↓
HARVESTED / LOST
```

For the first implementation, `FLOWER` may live primarily at truss level and fruits can be instantiated at `FRUIT_SET`.

---

# 16. Fruit Set

Once a truss enters fruit-setting stage, it creates a probabilistic number of fruits over several days.

Example model:

```text
potential_fruit_count
    ~ bounded distribution
```

Each potential fruit has a probability of successful set depending on:

```text
base fruit-set probability
× heat factor
× water factor
× plant health factor
```

This naturally makes severe stress reduce future yield without requiring explicit scenario scripting.

The first version may simplify this further by sampling the final fruit count once per truss.

---

# 17. Fruit Growth

Fruit size should follow a bounded growth curve rather than a constant daily increment.

Conceptually:

```text
diameter(age)
    = target_diameter × sigmoid(development_age)
```

or another simple saturating growth function.

The important qualitative behaviour is:

```text
small initial growth
        ↓
rapid middle growth
        ↓
slower growth near mature size
```

Each fruit should sample individual properties when created:

```text
target_diameter_mm
target_mass_g
development_speed
ripening_threshold
```

This produces natural variation within and between trusses.

---

# 18. Fruit Mass

Fruit mass can initially be derived from diameter.

A simple approximation is:

```text
mass_g = mass_coefficient × diameter_mm³
```

The coefficient is a configurable calibration constant.

Alternatively, target mass may be sampled directly and interpolated using the same growth curve.

The model should prioritize internal consistency over botanical precision.

---

# 19. Ripening

Ripening should be based primarily on accumulated physiological development.

It should **not** be modeled as an unrelated coin flip every day.

A fruit might have thresholds such as:

```text
mature_green_threshold
breaker_threshold
turning_threshold
red_threshold
overripe_threshold
```

Daily development advances according to:

```text
ripening_progress
    += temperature_factor
     × stress_factor
     × fruit_development_speed
```

Small stochastic variation should be sampled when the fruit is created rather than introducing large independent randomness every day.

This creates smooth and reproducible fruit development.

---

# 20. Harvestability

A fruit is considered harvestable when it reaches an acceptable ripeness stage.

For example:

```text
TURNING or RED
```

depending on configuration.

A truss may be considered harvestable when:

```text
harvestable fruit mass >= threshold
```

or:

```text
fraction of ripe fruits >= threshold
```

These values should be configurable because harvesting strategies differ.

---

# 21. Harvest Action

Harvest is a world-state-changing action.

Example:

```python
Harvest(
    plant_id="plant_017",
    fruit_ids=[...]
)
```

or at a higher level:

```python
HarvestRipeFruit(
    plant_id="plant_017",
    minimum_stage="RED"
)
```

The action:

```text
marks fruits HARVESTED
records harvest day
adds fruit mass to cumulative harvest
updates truss state if appropriate
```

Harvested fruits no longer exist in subsequent visual observations.

This is a crucial consistency requirement.

The simulator must never keep reporting harvested fruits merely because a scenario fixture says they existed previously.

---

# 22. Substrate / Soil Water Model

The first version uses a simplified water reservoir for each plant.

Conceptually:

```python
SubstrateState
    water_content
    water_capacity
    drainage_rate
```

Daily water balance:

```text
water(t+1)
    = water(t)
    + irrigation
    - evapotranspiration
    - drainage
```

Values are bounded by:

```text
0 <= water <= capacity
```

No detailed soil physics is required.

---

# 23. Evapotranspiration Approximation

Daily water consumption can depend on:

```text
base consumption
× plant_size_factor
× temperature_factor
× humidity_factor
```

Conceptually:

```text
hotter + drier air
    → higher water loss

larger plant
    → higher water loss
```

A small plant-specific stochastic multiplier may be used.

---

# 24. Water Stress

Water stress should emerge from latent substrate state.

For example:

```text
adequate water
    → stress ≈ 0

moderately low water
    → stress increases gradually

very low water
    → strong stress
```

The relationship should be smooth rather than binary.

Conceptually:

```python
water_stress = stress_curve(substrate_water_fraction)
```

Water stress can affect:

- stem growth;
- fruit development speed;
- fruit-set probability;
- wilting;
- potentially fruit loss under severe conditions.

---

# 25. Watering Action

Watering modifies hidden substrate state.

Example:

```python
WaterPlant(
    plant_id="plant_017",
    volume_ml=700
)
```

The simulator converts irrigation volume into reservoir replenishment.

The action should **not directly set the soil-moisture sensor output**.

Instead:

```text
watering action
    ↓
latent substrate water increases
    ↓
next sensor observation reflects higher moisture + noise
```

This preserves causal consistency.

---

# 26. Greenhouse Climate Model

The climate model should be deliberately simple but spatially coherent.

The greenhouse has a two-dimensional coordinate system:

```text
x ∈ [0, width]
y ∈ [0, length]
```

Each day has global environmental drivers such as:

```text
outside_temperature_c
solar_gain
heating_power
ventilation_factor
outside_humidity
```

These drivers produce greenhouse-level and spatial climate values.

---

# 27. Outside Temperature

Outside temperature may follow a smooth stochastic time series rather than independent daily samples.

Example:

```text
T_out(day+1)
    = seasonal / baseline term
    + autocorrelated variation
    + random noise
```

For a 28-day POC, a simple autoregressive model is sufficient.

This should naturally create several-day warm and cool periods.

---

# 28. Greenhouse Base Temperature

A simplified greenhouse mean temperature can be derived as:

```text
T_greenhouse_base
    = outside_temperature
    + solar_gain
    + heating_gain
    - ventilation_loss
```

The exact coefficients are simulation parameters.

The goal is plausible temporal behaviour rather than thermodynamic accuracy.

---

# 29. Spatial Temperature Field

Instead of giving every plant the same temperature, the simulator produces a smooth spatial field.

Conceptually:

```text
T(x, y)
    = base_temperature
    + heater_effect(x, y)
    - wall_loss(x, y)
    + spatial_noise(x, y)
```

This produces correlated differences between plants.

Example effects:

- plants closer to heating pipes are slightly warmer;
- plants near greenhouse walls are slightly cooler;
- neighbouring plants have similar temperatures.

The POC does not attempt CFD or realistic greenhouse thermodynamics.

---

# 30. Heating Sources

Heating sources can be represented geometrically.

Example:

```python
HeatingPipe
    start_position
    end_position
    power
    influence_radius
```

Temperature contribution may simply decay with distance from the pipe.

For example:

```text
heater_effect
    = heating_power × exp(-distance / decay_length)
```

One or two virtual pipes are sufficient for the primary simulation.

The exact placement is a configuration detail.

---

# 31. Wall Loss

A plant's temperature may be slightly lower near greenhouse boundaries.

A simple model can derive:

```text
distance_to_nearest_wall
```

and apply a smooth boundary effect.

This creates a useful spatial gradient with very little complexity.

---

# 32. Relative Humidity

Relative humidity can initially be modeled at greenhouse level with modest spatial variation.

It may depend approximately on:

```text
outside humidity
ventilation
internal temperature
crop transpiration
```

The first version can simplify this substantially.

What matters is that humidity varies smoothly over time and is not an independent random number at every plant every day.

---

# 33. Heat Stress

Plant heat stress should derive from experienced temperature.

Conceptually:

```text
comfortable range
    → no heat stress

above threshold
    → stress increases with magnitude and duration
```

At daily resolution, useful derived quantities can include:

```text
daily_mean_temperature
max_temperature
estimated_hours_above_threshold
```

Heat stress may affect:

- fruit set;
- plant growth;
- water use;
- fruit development;
- wilting.

---

# 34. Daily Simulation Order

The exact ordering matters for causal consistency.

Recommended daily sequence:

```text
1. Advance simulation clock

2. Generate daily external climate drivers

3. Build greenhouse spatial climate field

4. Apply scheduled morning actions if any
   - watering
   - harvesting
   - lowering
   - pruning

5. Update substrate water balance

6. Compute plant water / heat stress

7. Advance plant physiological development

8. Advance stem growth

9. Create new trusses where appropriate

10. Advance truss development

11. Set new fruits where appropriate

12. Advance existing fruit growth

13. Advance fruit ripening

14. Apply biological consequences / losses

15. Apply later operational actions if required

16. Finalize hidden end-of-day ground truth

17. Generate sensor observations

18. Generate simulated vision observations

19. Generate externally visible operational events

20. Persist hidden truth separately from platform-facing data
```

The implementation may adjust exact ordering if tests show a cleaner interpretation, but it should remain explicit and documented.

---

# 35. Actions

The first simulator should support the following action types.

## Water

```text
WATER
```

Effects:

- increases substrate water;
- records intervention;
- indirectly influences future stress and observations.

## Harvest

```text
HARVEST
```

Effects:

- removes selected harvestable fruits from active plant state;
- increments cumulative harvest;
- changes subsequent visual observations.

## Lower Plant

```text
LOWER_PLANT
```

Effects:

- increases lowered stem length;
- records management event;
- does not reset biological growth.

## Prune

```text
PRUNE
```

Initial effects may be minimal:

- reduce modeled leaf-area factor;
- record management event.

Pruning can remain optional in the first milestone.

---

# 36. Action Sources

Actions may have a source:

```text
SIMULATION_OPERATOR
HUMAN
ROBOT
AUTOMATION
```

For the initial world model, actions are generated by the simulator's management policy.

Later, some can deliberately be hidden from the platform-facing event stream to evaluate event inference.

---

# 37. Management Policy

The simulation needs a basic policy for deciding when actions happen.

This policy represents the simulated grower/operator, not the intelligence platform being evaluated.

Examples:

### Irrigation

```text
if latent substrate water < management threshold:
    water plant
```

or watering can be scheduled by greenhouse zone.

### Harvest

```text
if harvestable fruit mass > threshold:
    harvest ripe fruit
```

### Lowering

```text
if effective vertical height > management threshold:
    lower plant by configured amount
```

The policy should be deliberately simple and deterministic given world state + random seed.

Later versions can generate imperfect management behaviour such as missed watering or delayed harvest.

---

# 38. Observation Model

After the hidden world has advanced, the simulator generates **platform-facing observations**.

There should be at least three categories:

```text
environmental sensor observations
plant-level soil observations
visual plant observations
```

Operational events are emitted separately.

---

# 39. Environmental Sensor Observation

Example:

```json
{
  "greenhouse_id": "greenhouse_001",
  "timestamp": "day_14",
  "air_temperature_c": 27.4,
  "relative_humidity_pct": 68.2
}
```

Sensor output should differ slightly from hidden true climate values.

Example:

```text
observed_temperature
    = true_temperature_at_sensor
    + measurement_noise
```

---

# 40. Soil-Moisture Observation

Example:

```json
{
  "plant_id": "plant_017",
  "timestamp": "day_14",
  "soil_moisture_pct": 43.1
}
```

This is derived from hidden substrate state plus sensor noise and optional calibration bias.

Conceptually:

```text
measurement
    = transform(hidden_water_fraction)
    + sensor_bias
    + daily_noise
```

Each sensor can sample a small persistent bias when created.

That is preferable to completely independent noise every day.

---

# 41. Simulated Vision Observation

No images are generated or analyzed in this POC.

Instead, the simulator generates structured values representing what a future CV pipeline might output.

Example:

```json
{
  "plant_id": "plant_017",
  "timestamp": "day_14",

  "visible_fruit_count": 41,
  "green_fruit_count": 22,
  "ripening_fruit_count": 9,
  "ripe_fruit_count": 10,

  "average_fruit_diameter_mm": 19.4,
  "estimated_visible_fruit_mass_g": 1740,

  "leaf_wilting_score": 0.16,
  "leaf_discoloration_score": 0.04
}
```

The observation should be generated from hidden plant state, not independently.

---

# 42. Vision Noise

The visual observation model should introduce plausible imperfections.

Examples:

```text
some fruits are missed
fruit count has small error
size estimates have measurement noise
ripeness classification is occasionally off by one stage
wilting estimate has noise
```

The first implementation should keep these errors modest.

The goal is to prevent the platform from receiving perfect ground truth while keeping evaluation understandable.

---

# 43. Fruit Tracking IDs

Ground truth contains stable `fruit_id` values.

The first platform-facing observation does **not need to expose individual fruit tracks**.

Aggregate counts are enough for the first milestone.

A later extension may generate:

```text
vision_track_id
```

with imperfect persistence across days.

This would enable evaluation of fruit tracking without requiring actual images.

---

# 44. Wilting Observation

Wilting is derived primarily from water and heat stress.

Conceptually:

```text
true_wilting
    = f(water_stress, heat_stress)
```

Then:

```text
observed_wilting
    = true_wilting + vision_noise
```

The output should be normalized, for example:

```text
0.0 = no visible wilting
1.0 = severe wilting
```

---

# 45. Hidden Ground Truth

For evaluation, the simulator should retain a detailed daily snapshot of hidden world state.

Example information:

```text
true plant water state
true stress values
true fruit identities
true fruit sizes
true ripeness stages
true harvested fruits
true actions
true temperature at plant position
```

This store is strictly separate from platform-facing data.

It should never be accessible to the intelligence layer under evaluation.

---

# 46. Persistence Outputs

A simulation run may produce two conceptual outputs.

## Simulation Ground Truth

```text
ground_truth/
```

Used by:

- simulator tests;
- evaluation;
- debugging.

## Platform Input

```text
observations/
events/
```

Used by:

- state reconstruction;
- intelligence;
- dashboard;
- later chatbot analytics.

This boundary should remain explicit in code.

---

# 47. Parameterization

Simulation behaviour should be defined through configuration rather than scattered magic numbers.

Conceptual configuration groups:

```text
greenhouse
climate
plant
truss
fruit
water
management
observation_noise
```

Example:

```yaml
plant:
  base_stem_growth_cm_per_day: 2.4
  truss_interval_effective_days: 6.5

fruit:
  target_diameter_mean_mm: 24
  target_diameter_std_mm: 2
  ripening_start_effective_day: 32

water:
  substrate_capacity: 1.0
  irrigation_threshold: 0.35

simulation:
  seed: 42
  duration_days: 28
```

Numbers above are examples only.

The final values should be clearly labeled as simulator parameters rather than validated agronomic constants.

---

# 48. Individual Variation

Plants should not be clones.

At initialization, each plant can sample persistent multipliers such as:

```text
growth_rate_multiplier
water_consumption_multiplier
fruit_set_multiplier
fruit_size_multiplier
ripening_speed_multiplier
```

Example:

```text
plant 01 growth multiplier = 0.96
plant 02 growth multiplier = 1.04
```

These values stay fixed throughout the simulation.

This creates believable diversity while maintaining temporal consistency.

---

# 49. Correlated Randomness

Avoid generating independent random values everywhere.

Prefer persistent or autocorrelated variation.

Examples:

- hot weather lasts several days;
- a sensor's calibration bias persists;
- a slower-growing plant remains somewhat slower;
- neighbouring plants experience similar temperature;
- fruit development varies by fruit but remains smooth.

This is one of the most important properties for producing useful longitudinal data.

---

# 50. No Scenario Scripting Required for Normal Behaviour

The baseline simulator should naturally generate healthy greenhouse development without explicit scenarios.

A normal run should emerge from:

```text
climate dynamics
+
plant dynamics
+
management policy
+
observation noise
```

rather than commands such as:

```text
Day 7: Plant 4 becomes stressed
Day 9: Plant 8 grows fruit
```

Explicit scenario injections may later modify model parameters or actions, but should not replace the generative model.

---

# 51. Future Scenario Injection

Once baseline dynamics work, abnormal scenarios should preferably be introduced by changing causes rather than directly setting outcomes.

Example: heat wave

```text
raise outside temperature for 4 days
```

not:

```text
set heat_stress = true
```

Example: irrigation failure

```text
disable watering for Zone 2
```

not:

```text
set plants 11–20 to water_stressed
```

Example: delayed harvest

```text
suppress harvest action for 3 days
```

not:

```text
set fruit_count high
```

This keeps causal relationships meaningful.

---

# 52. Disease — Deferred

Disease is explicitly excluded from the first simulator milestone.

The healthy / abiotic-stress baseline should work first.

Later, disease can be introduced as a latent process that affects existing plant properties such as:

```text
leaf discoloration
leaf area
growth rate
fruit development
fruit loss
water use
```

This is preferable to a simple:

```text
disease = true
```

flag.

---

# 53. Minimal First Milestone

The first useful version of the simulator should support:

```text
1. Create configurable greenhouse grid.

2. Create 40 individual plants.

3. Simulate 28 daily steps.

4. Generate smooth outside / greenhouse temperatures.

5. Generate spatial temperature differences.

6. Maintain substrate water for each plant.

7. Apply automatic watering.

8. Grow plant stems.

9. Generate trusses over time.

10. Generate fruits on trusses.

11. Grow individual fruits.

12. Progress fruit ripeness.

13. Harvest ripe fruit according to management policy.

14. Lower plants when appropriate.

15. Maintain cumulative harvest.

16. Generate environmental sensor observations.

17. Generate soil-moisture observations.

18. Generate structured visual observations.

19. Add realistic measurement noise.

20. Persist ground truth separately from observations.

21. Produce identical runs for identical seeds.
```

---

# 54. Minimal Demonstration

A simple CLI or notebook-level test should be able to run:

```text
create simulation(seed=42)
run 28 days
```

and produce a summary such as:

```text
Simulation Greenhouse 001
28 days completed

Plants: 40
Trusses created: 183
Fruits created: 2,146
Fruits harvested: 487
Harvested mass: 6.3 kg

Plant 17:
  stem length: 168 cm
  lowered: 35 cm
  active trusses: 4
  visible fruit: 51
  ripe fruit: 9
  cumulative harvest: 320 g
  soil moisture: 47%
```

The values themselves are not important initially.

What matters is that they arise coherently from the model.

---

# 55. Validation Invariants

The simulator should include deterministic consistency checks.

Examples:

```text
harvested fruit cannot become visible again

fruit mass cannot be negative

fruit diameter cannot be negative

substrate water must remain within bounds

cumulative harvest cannot decrease

fruit cannot belong to multiple trusses

truss must belong to exactly one plant

plant IDs remain stable

fruit IDs remain stable until terminal state

simulation day always increases monotonically
```

These invariants should become automated tests early.

---

# 56. Architecture Suggestion

A possible package structure is:

```text
simulation/
    config/
        models.py
        defaults.py

    domain/
        greenhouse.py
        plant.py
        truss.py
        fruit.py
        substrate.py
        climate.py
        actions.py

    dynamics/
        climate.py
        plant_growth.py
        truss_growth.py
        fruit_growth.py
        water.py
        stress.py

    management/
        policy.py
        irrigation.py
        harvest.py
        lowering.py

    observations/
        environment.py
        soil.py
        vision.py
        noise.py

    engine/
        world.py
        runner.py
        step.py

    persistence/
        ground_truth.py
        observations.py

    tests/
        test_determinism.py
        test_invariants.py
        test_harvest.py
        test_water.py
        test_growth.py
```

The exact structure is not mandatory.

The important conceptual separation is:

```text
world dynamics
≠
management actions
≠
observation generation
```

---

# 57. Recommended Implementation Order

Do not attempt to implement every part simultaneously.

Recommended sequence:

```text
1. Core data models
      ↓
2. Simulation clock + deterministic RNG
      ↓
3. Greenhouse + plant initialization
      ↓
4. Climate evolution
      ↓
5. Stem / physiological growth
      ↓
6. Truss creation
      ↓
7. Fruit creation and growth
      ↓
8. Ripening
      ↓
9. Water reservoir + watering
      ↓
10. Harvest
      ↓
11. Lowering
      ↓
12. Observation generation
      ↓
13. Noise
      ↓
14. Persistence
      ↓
15. Validation tests
```

The first meaningful milestone is not a dashboard.

It is:

```text
seed = 42
    ↓
create greenhouse
    ↓
simulate 28 days
    ↓
obtain a coherent hidden history
    ↓
obtain noisy platform-facing observations
```

---

# 58. Definition of Done

The baseline simulation engine is complete when:

- the same seed reproduces the same run;
- greenhouse layout is configurable;
- plants remain individually identifiable;
- stems develop over time;
- trusses appear naturally from development;
- fruits are created and retain identity;
- fruits grow smoothly rather than jumping randomly;
- ripening progresses over time;
- temperature evolves smoothly and spatially;
- water state evolves causally;
- watering changes latent water state;
- stress emerges from environmental conditions;
- harvesting removes real hidden fruits;
- harvested fruits disappear from later observations;
- lowering is represented as an action;
- sensor observations contain controlled noise;
- vision observations are derived from actual hidden plant state;
- hidden ground truth is isolated from platform-facing observations;
- basic simulation invariants are covered by automated tests.

At that point, the project has a genuine **probabilistic greenhouse world model** rather than a collection of generated fixtures.

---

# 59. Future Extensions

Once the baseline works, likely extensions include:

- imperfect or delayed management actions;
- irrigation zones rather than plant-by-plant watering;
- heat waves;
- ventilation failures;
- sensor failures and drift;
- hidden actions;
- pruning effects;
- fruit loss;
- disease progression;
- spatial disease propagation;
- individual fruit tracking observations;
- camera occlusion models;
- weather feeds;
- more realistic greenhouse climate control;
- calibrated tomato-development parameters;
- configurable crop types;
- sub-daily simulation if required.

These should be introduced incrementally rather than complicating the first simulator.

---

# 60. Final Design Principle

The simulator should answer one question:

> **Given a simplified model of a real greenhouse, what could plausibly happen next, and what would our sensors observe?**

It should not attempt to answer:

> **What should the grower do?**

The first question belongs to the simulator.

The second belongs to the greenhouse intelligence platform.

Keeping that boundary clean is essential for meaningful evaluation later.
