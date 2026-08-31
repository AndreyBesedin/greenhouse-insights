# Greenhouse Simulation — Design Document

## 1. Purpose

This document defines the logical simulation used by the Greenhouse Intelligence Platform.

The simulator is a **generative world model**, not a scripted scenario player.

Its job is to maintain a hidden representation of greenhouse reality, advance that reality one simulation step at a time, apply actions, and emit noisy observations similar to what a future real system would receive from sensors, cameras, operators, and automation systems.

The current simulation step is:

```text
1 simulation step = 1 day
```

The simulator should be deterministic for a given random seed while still producing probabilistic variation.

The design must support a later management-policy layer, including an agentic greenhouse assistant. The simulator itself must remain independent from any LLM or agent framework.

Core principle:

> The simulator models what happens.
> A management policy decides what should happen.
> The agent is one possible implementation of that policy.

---

# 2. Main Architectural Separation

The simulator owns the hidden world state.

The application and management systems operate only through observable state and explicit actions.

```text
Hidden greenhouse world
        ↓
Daily world transition
        ↓
Observation generation
        ↓
Reconstructed / observable state
        ↓
Management policy
        ↓
Requested actions
        ↓
Validation
        ↓
Accepted actions
        ↓
Simulator applies actions
        ↓
Next simulation step
```

The management policy may initially be:

```text
No management
Rule-based management
Agentic management
```

The simulator must not care which policy generated an action.

---

# 3. Simulation Goals

The first simulator should support:

- configurable greenhouse grids;
- vine / cherry tomato plants;
- daily plant development;
- truss creation;
- individual fruit creation and tracking;
- fruit growth;
- fruit ripening;
- soil-water dynamics;
- greenhouse temperature and humidity;
- simple spatial climate variation;
- watering;
- harvesting;
- plant lowering;
- inspections;
- noisy sensor observations;
- noisy vision-derived observations;
- deterministic seeded execution;
- persisted world history;
- persisted observations;
- persisted actions;
- compatibility with a future agentic management layer.

The simulator is not intended to be a scientifically calibrated crop model.

It should be biologically plausible enough to generate coherent longitudinal data.

---

# 4. Non-Goals

The first simulator does not attempt to provide:

- second-by-second dynamics;
- detailed greenhouse HVAC physics;
- scientifically accurate tomato yield prediction;
- detailed plant geometry;
- raw image rendering;
- computer vision;
- disease epidemiology;
- nutrient chemistry;
- full hydroponic modelling;
- robotics;
- motion planning;
- automatic climate optimization;
- sophisticated labour planning.

These may be added later.

---

# 5. Time Model

Simulation time is discrete.

```text
1 step = 1 day
```

A run may contain, for example:

```text
28 days
40 days
90 days
```

depending on the simulation definition.

The simulator should not assume that all runs have the same duration.

Conceptually:

```python
for day in simulation_days:
    advance_world(day)
    generate_observations(day)
    reconstruct_observable_state(day)
    run_management_policy(day)
    validate_actions(day)
    apply_actions(day)
    persist(day)
```

The exact order may be refined during implementation, but management must occur once per simulation step.

---

# 6. Hidden World Model

The simulator owns the true state of the greenhouse.

This hidden state is not directly exposed to the intelligence system or agent.

Conceptually:

```text
GreenhouseWorld
    ├── environment
    ├── climate field
    ├── plants
    ├── soil / substrate state
    ├── historical actions
    └── simulation metadata
```

---

# 7. Greenhouse

A greenhouse has:

```text
greenhouse_id
name

width
length

rows
plants

crop_type

environment_model
climate_model

simulation_seed
simulation_day
```

Plants must have stable identities and positions.

Example:

```json
{
  "plant_id": "plant_017",
  "row": 2,
  "position_in_row": 7,
  "x": 6.0,
  "y": 2.0
}
```

Position is initially used for organization and climate sampling.

Detailed geometry is not required.

---

# 8. Plant Model

A vine tomato plant should be represented structurally rather than geometrically.

Conceptual model:

```text
Plant
    id
    position

    age_days

    stem_length_cm
    lowered_length_cm

    development_stage

    water_status
    health_state

    trusses[]

    cumulative_harvest_g
```

Derived vertical height may be:

```text
visible_vertical_height
=
stem_length_cm - lowered_length_cm
```

This is sufficient for the POC.

---

# 9. Truss Model

Vine tomatoes naturally lend themselves to truss-level modelling.

A plant contains a sequence of trusses.

```text
Truss
    id
    plant_id
    index

    age_days
    developmental_stage

    fruits[]
```

Possible stages:

```text
initiated
flowering
fruit-setting
fruiting
harvestable
inactive
```

A new truss may appear after a configurable number of effective growing days.

---

# 10. Fruit Model

Each fruit has a stable hidden identity.

```text
Fruit
    id
    plant_id
    truss_id

    age_days

    diameter_mm
    mass_g

    ripeness
    status

    target_diameter_mm
    development_speed
```

Possible statuses:

```text
growing
ripe
harvested
aborted
```

Fruit identity belongs to hidden simulation truth.

Future computer-vision observations may have their own tracking identifiers.

---

# 11. Fruit Growth

Fruit growth should use a bounded growth curve rather than a constant increment.

Conceptually:

```text
diameter(age)
=
target_diameter
×
growth_curve(effective_age)
```

The curve may initially be implemented using a simple sigmoid or other bounded function.

Mass can be approximated as:

```text
mass ≈ k × diameter³
```

Each fruit samples slightly different parameters at creation:

```text
target diameter
growth rate multiplier
ripening threshold
final mass variation
```

This creates natural variability while preserving deterministic replay through the simulation seed.

---

# 12. Fruit Ripening

Ripening should primarily depend on fruit developmental age rather than an independent daily probability.

Possible conceptual stages:

```text
fruit_set
    ↓
immature_green
    ↓
mature_green
    ↓
breaker
    ↓
turning
    ↓
ripe
    ↓
overripe
```

Temperature may modify effective developmental speed.

Thresholds should contain seeded individual variation.

Example conceptual parameters:

```text
ripening_start_day ~ distribution
full_ripe_day ~ distribution
```

Exact biological values remain configurable and should not be treated as scientifically calibrated constants.

---

# 13. Plant Stem Growth

Each day the plant gains stem length according to:

```text
base growth
×
temperature factor
×
water-status factor
×
plant-specific variation
```

The initial implementation may keep this simple.

Stem growth contributes to truss initiation.

---

# 14. Plant Lowering

Commercial vine tomatoes are progressively lowered as the stem grows.

Represent this as a management action.

```text
LowerPlant
    plant_id
    amount_cm
```

Applying it changes:

```text
lowered_length_cm
```

It does not remove trusses or fruits and does not reset biological age.

The first implementation does not need detailed stem geometry on the ground.

---

# 15. Soil / Substrate Water Model

Each plant should have a simplified water reservoir.

Conceptually:

```text
water(t+1)
=
water(t)
+ irrigation
- plant_water_use
- evaporation
- drainage
```

Plant water use may depend on:

```text
temperature
humidity
plant size
fruit load
```

The exact physical units may remain approximate for the POC.

The important behaviour is causal consistency.

For example:

```text
hot day
→ increased water demand
→ substrate moisture falls
→ prolonged deficit
→ latent water stress rises
→ wilting observation rises
```

Watering changes hidden reservoir state rather than directly setting a sensor reading.

---

# 16. Plant Water Stress

Each plant maintains a latent water-stress value.

Conceptually:

```text
water_stress ∈ [0, 1]
```

It should increase when substrate moisture remains below an effective threshold and recover when water availability improves.

Water stress can influence:

- stem growth;
- fruit development;
- wilting;
- health status.

Do not make water stress flip instantly from healthy to stressed based on one reading.

Temporal persistence is preferred.

---

# 17. Greenhouse Climate Model

The climate model should remain simple but spatially correlated.

Represent the greenhouse as a two-dimensional coordinate system.

```text
x ∈ [0, width]
y ∈ [0, length]
```

Each day define greenhouse-level drivers such as:

```text
outside_temperature
solar_gain
heating_power
ventilation_level
outside_humidity
```

Then derive a spatial temperature field.

Conceptually:

```text
T(x, y)
=
base_temperature
+ heater_effect(x, y)
+ solar_effect(x, y)
- wall_loss(x, y)
+ spatial_noise(x, y)
```

This does not need to be physically rigorous.

Its purpose is to create meaningful spatial correlations.

---

# 18. Heating Model

For the POC, represent one or more virtual heat sources.

Possible configuration:

```text
heater pipes
heating lines
central heating source
```

Each heat source has:

```text
position
strength
falloff
```

Plants closer to the source may be modestly warmer.

The model should be configurable rather than hard-coded.

---

# 19. Greenhouse Walls

Plants closer to greenhouse boundaries may experience greater thermal loss.

A simplified wall-loss function can depend on distance to the nearest greenhouse boundary.

Example conceptual relationship:

```text
wall_loss
∝
1 / distance_to_wall
```

Use bounded values.

Do not attempt full heat-transfer physics.

---

# 20. Humidity

Greenhouse-level relative humidity should vary with:

```text
outside humidity
temperature
plant transpiration
ventilation
```

A simple stochastic model is sufficient.

Plant-level humidity can initially be sampled from the greenhouse climate field with small local variation.

---

# 21. Environmental Evolution

Daily outside conditions should evolve smoothly rather than independently randomizing every day.

Possible approach:

```text
today_temperature
=
yesterday_temperature
+ small random drift
+ occasional weather pattern
```

The same applies to humidity.

This creates coherent weather periods.

---

# 22. Actions

Actions are first-class domain objects.

Initial V1-compatible action set:

```text
WATER_PLANT
HARVEST_PLANT
LOWER_PLANT
SCHEDULE_INSPECTION
```

The simulator is responsible for defining how accepted actions alter the world.

---

# 23. Water Plant Action

Conceptual schema:

```text
WaterPlant
    plant_id
    amount_ml
```

Effects:

- increases plant substrate-water reservoir;
- may create drainage if excessive;
- affects future plant stress;
- is persisted in action history.

---

# 24. Harvest Plant Action

Harvesting operates at plant level for the POC.

Conceptual request:

```text
HarvestPlant
    plant_id
    target = ripe
```

The simulator determines which eligible fruits are removed.

Effects:

- eligible ripe fruits become `harvested`;
- visible fruit count decreases;
- ripe mass decreases;
- cumulative harvest increases;
- action is recorded.

The management policy does not need to select individual fruits or trusses.

---

# 25. Lower Plant Action

Conceptual schema:

```text
LowerPlant
    plant_id
    amount_cm
```

Effects:

- increases `lowered_length_cm`;
- preserves plant biological state;
- creates an operational event.

---

# 26. Schedule Inspection Action

Conceptual schema:

```text
ScheduleInspection
    plant_id
    reason
```

For the simulation POC, this may simply generate a recorded operational event.

Later it may interact with:

- human workflows;
- labour scheduling;
- additional observations.

---

# 27. Action Provenance

Every action must preserve its source.

Possible sources:

```text
HUMAN
RULE_BASED_POLICY
AGENT
SIMULATION_INTERNAL
ROBOT
```

Agent-generated actions should therefore be persisted with:

```text
source = AGENT
```

This allows the UI and evaluations to distinguish them.

---

# 28. Action Boundary

The simulator should expose an explicit action interface.

Conceptually:

```python
available_actions(...)
validate_action(...)
apply_action(...)
```

The simulator must not invoke an agent directly.

Bad architecture:

```python
simulation.ask_agent_what_to_do()
```

Preferred architecture:

```python
actions = management_policy.decide(context)

for action in actions:
    validated = action_validator.validate(action)

    if validated:
        simulation.apply_action(action)
```

---

# 29. Action Validation

All policy-generated actions pass through a validation layer.

Validation is outside the LLM prompt.

Examples:

```text
plant must exist
water amount must be positive
water amount must remain below configured maximum
lowering amount must be physically allowed
unsupported actions are rejected
```

Hard operational constraints should be enforced in code.

Soft preferences may additionally be included in management-policy configuration or prompts.

---

# 30. Management Policy Compatibility

The simulator should support a policy interface from the beginning.

Conceptually:

```python
class ManagementPolicy(Protocol):
    def decide(
        self,
        context: GreenhouseManagementContext,
    ) -> list[RequestedAction]:
        ...
```

Initial implementations may include:

```text
NoOpPolicy
DeterministicPolicy
AgenticPolicy
```

The `AgenticPolicy` belongs to a separate module and design document.

---

# 31. Policy Timing

The management policy runs once per simulation step.

For the current POC:

```text
once per day
```

Conceptual daily flow:

```text
START DAY
    ↓
advance environment
    ↓
advance biological state
    ↓
generate observations
    ↓
derive / reconstruct observable state
    ↓
management policy evaluates current state
    ↓
policy requests zero or more actions
    ↓
validate actions
    ↓
apply accepted actions
    ↓
persist world + observations + actions
    ↓
END DAY
```

Actions affect subsequent world state and observations.

---

# 32. Observable State

The agent or deterministic management policy must not receive hidden simulation truth.

It receives the same kind of information a production system could plausibly provide.

Examples:

```text
greenhouse metadata
greenhouse summary
plant state
plant history
recent observations
recent actions
active alerts
derived trends
```

Private simulator values remain inaccessible.

Example hidden truth:

```text
true fruit diameter = 27.328 mm
true latent water stress = 0.417
```

Possible observable values:

```text
estimated fruit diameter = 28.1 mm
soil moisture sensor = 31%
wilting score = 0.36
water stress = moderate
```

---

# 33. Observation Model

The simulator generates observations from hidden world state.

This is a separate stage.

```text
Hidden world
    ↓
Observation model
    ↓
Platform input
```

The observation model introduces:

```text
measurement noise
missing observations
detection uncertainty
tracking uncertainty
```

The first implementation may only require measurement noise.

---

# 34. Sensor Observations

Initial sensor outputs:

```text
air_temperature_c
relative_humidity_pct
soil_moisture_pct
```

Example:

```json
{
  "plant_id": "plant_017",
  "day": 12,
  "air_temperature_c": 29.1,
  "relative_humidity_pct": 67.4,
  "soil_moisture_pct": 34.7
}
```

Noise should be sampled deterministically from the simulation random generator.

---

# 35. Vision-Derived Observations

No raw images are generated.

Instead, simulate the output of a future perception system.

Possible observations:

```text
visible_fruit_count
green_fruit_count
ripening_fruit_count
ripe_fruit_count
average_fruit_diameter_mm
estimated_visible_fruit_mass_g
wilting_score
leaf_discoloration_score
```

These should be noisy approximations of hidden truth.

---

# 36. Hidden Fruit IDs vs Observed Tracking IDs

Hidden fruits have stable simulator IDs.

Example:

```text
fruit_017_06_04
```

Future visual observations may instead expose tracking IDs.

Example:

```text
vision_track_938
```

The first POC does not need to simulate tracking errors.

However, do not make hidden fruit IDs part of the public observation contract.

This preserves the ability to add realistic matching problems later.

---

# 37. Observation Noise

Noise should be configurable by sensor type.

Example:

```text
temperature noise: small Gaussian
soil moisture noise: larger Gaussian
fruit count: occasional ±1 detection error
diameter: bounded measurement noise
```

Do not hard-code noise directly inside plant models.

Use an explicit observation-model layer.

---

# 38. Simulation Determinism

Given:

```text
same simulation configuration
same random seed
same management policy
same external actions
```

the simulator should produce the same run.

This is critical for:

- debugging;
- evaluation;
- comparing management policies;
- demonstrations.

All stochastic behaviour should derive from an explicit seeded random generator.

---

# 39. Persistence

Persist enough information to reconstruct and inspect a run.

Recommended persisted concepts:

```text
simulation_definition
simulation_run
world snapshots
observations
actions
observable state snapshots
simulation progress
```

World snapshots may initially be stored once per simulated day.

The persistence implementation can later be optimized.

---

# 40. Simulation Runs

A greenhouse simulation should distinguish the simulation definition from an execution.

Example:

```text
SimulationDefinition
    greenhouse configuration
    duration
    seed
    biological parameters
    climate parameters
```

and:

```text
SimulationRun
    run_id
    definition_id
    status
    current_day
    started_at
    completed_at
```

This makes policy comparisons possible later.

---

# 41. Policy Comparison Runs

Eventually, the same simulation definition may be executed under:

```text
No management
Deterministic baseline
Agentic policy
```

Using the same seed makes comparisons meaningful.

The architecture should allow this even if the first UI only exposes one run.

---

# 42. Progressive Execution

Simulation should support progressive rather than instantaneous execution.

Recommended demo behaviour:

```text
1 simulated day ≈ 1 second
```

This delay is presentation-oriented and configurable.

Backend logic should not fundamentally depend on sleeping between steps.

---

# 43. Simulation Progress Events

The backend should expose progress while a run is executing.

At minimum:

```text
simulation_started
day_started
observations_generated
state_updated
management_started
management_progress
actions_selected
actions_applied
day_completed
simulation_completed
simulation_failed
```

Not every event needs to be persisted forever.

Some may exist only for UI streaming.

---

# 44. Agent / Management Latency

Agentic management may introduce latency greater than the normal simulation-step duration.

The simulation execution model must tolerate this.

For example:

```text
Day 12 / 28

Generating observations...
Analysing plants...
Selecting management actions...
Applying 2 actions...
Day completed
```

The simulation should wait for the management policy to finish before advancing to the next day.

A timeout / failure policy can be added later.

---

# 45. Streamed UI Feedback

The backend should expose enough state for the UI to explain why a simulation step is taking time.

The first agentic version does not need to expose private chain-of-thought.

Instead stream operational progress such as:

```text
Analysing greenhouse summary
Inspecting Plant 17
Inspecting Plant 31
Evaluating harvest opportunities
2 management actions selected
Applying actions
```

The UI should display high-level process events, not hidden model reasoning.

---

# 46. UI Progress Contract

Possible event payload:

```json
{
  "type": "management_progress",
  "simulation_run_id": "run_001",
  "day": 12,
  "status": "inspecting_plant",
  "plant_id": "plant_017",
  "message": "Reviewing Plant 17"
}
```

Another:

```json
{
  "type": "actions_selected",
  "simulation_run_id": "run_001",
  "day": 12,
  "action_count": 2
}
```

Transport may use:

```text
polling
Server-Sent Events
WebSocket
```

Implementation should prefer the simplest reliable solution.

---

# 47. Simulation Status

Possible run statuses:

```text
NOT_STARTED
RUNNING
COMPLETED
FAILED
```

Optional future status:

```text
PAUSED
```

While `RUNNING`, expose:

```text
current_day
total_days
current_phase
current_progress_message
```

---

# 48. Ground Truth

The simulator may retain private ground truth.

This can later support evaluations.

Examples:

```text
true plant stress
true fruit count
true intervention need
true harvestable mass
```

The management policy must not access this data.

Ground truth is evaluation-only.

---

# 49. Evaluation Hooks

Detailed policy evaluation belongs to the agentic-management phase.

However, simulator architecture should support it.

Useful hooks:

```text
expected management state
acceptable action ranges
true outcome metrics
water usage
harvest mass
health trajectory
```

These should be optional rather than mandatory for every simulator feature.

---

# 50. Recommended Package Boundaries

```text
simulation/
    world/
        greenhouse.py
        plant.py
        truss.py
        fruit.py
        environment.py

    dynamics/
        growth.py
        ripening.py
        water.py
        climate.py

    actions/
        models.py
        application.py

    observations/
        sensors.py
        vision.py
        noise.py

    runner/
        simulation_runner.py
        progress.py

    persistence/
        snapshots.py

management/
    policy.py
    no_op_policy.py
    deterministic_policy.py
    action_validator.py

management/agent/
    # V1, separate design document
```

Exact filenames are flexible.

The architectural boundaries are not.

---

# 51. Initial Deterministic Baseline

A simple deterministic management policy should exist once the management layer begins.

Possible rules:

```text
if soil moisture below threshold:
    water plant

if ripe mass above threshold:
    harvest plant

if plant height exceeds operational threshold:
    lower plant

if data is inconsistent:
    schedule inspection
```

This policy should use the same observable state available to the future agent.

It should not read hidden simulator truth.

---

# 52. First Simulator V0 Scope

V0 should focus on the physical/logical world before building the agent.

Required:

```text
greenhouse grid
plants
trusses
fruits

daily environment
temperature field
humidity

soil water
plant water stress

stem growth
truss initiation
fruit growth
fruit ripening

watering action
harvest action
lowering action
inspection action

sensor observations
vision-derived observations

seeded deterministic runs
persistence
progress events
```

The policy interface should exist, but V0 may run with:

```text
NoOpPolicy
```

or directly supplied test actions.

---

# 53. V1 Immediately After Simulator

After V0 is coherent, add the management layer.

V1 will introduce:

```text
GreenhouseManagementContext
ManagementPolicy interface
DeterministicPolicy
AgenticPolicy
read tools
action tools
action validation
provider abstraction
streamed management progress
basic evaluation
```

The separate agentic-management design document defines this layer.

---

# 54. Definition of Done — Simulator V0

A successful V0 should be able to:

1. create a configured greenhouse;
2. generate positioned vine tomato plants;
3. advance one simulated day at a time;
4. create trusses;
5. create individual fruits;
6. grow fruits;
7. ripen fruits;
8. maintain spatially varying climate;
9. evolve soil water;
10. develop and recover water stress;
11. apply watering;
12. apply plant-level harvesting;
13. apply plant lowering;
14. record inspections;
15. generate noisy sensor observations;
16. generate noisy vision-derived observations;
17. persist daily state;
18. persist actions with provenance;
19. produce identical runs from identical seeds and actions;
20. emit progress events suitable for the UI;
21. accept actions through a generic management-policy boundary;
22. remain completely independent from LLM providers.

---

# 55. Final Design Principle

The simulator should be simple enough to understand but rich enough to create meaningful causal histories.

The important chain is:

```text
environment
    ↓
hidden biological state
    ↓
observable measurements
    ↓
management decision
    ↓
validated action
    ↓
changed hidden state
    ↓
future observations
```

This makes the simulation useful both as a POC and as an evaluation environment for increasingly sophisticated greenhouse intelligence and management systems.
