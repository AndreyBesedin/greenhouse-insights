# Greenhouse Intelligence POC

## 1. Abstract

The long-term goal of the greenhouse project is to build an **intelligence and operational support platform for greenhouse production**.

The system should maintain a structured, longitudinal representation of one or more greenhouses and of the plants within them over time by combining environmental sensor data, plant-level measurements, visual observations, operational events and historical state.

Its purpose is to transform this continuously evolving representation into useful operational information. This includes identifying plants requiring attention, prioritising work, detecting health or disease risks, estimating upcoming harvests, forecasting workload and labour requirements, tracking production, and providing operators with a reliable understanding of how each greenhouse is evolving.

The consumers of these insights may be **human operators, greenhouse managers, external software systems, automated equipment or robots**. Robotic automation is therefore an optional downstream consumer of the intelligence produced by the platform, not the core objective of the project.

This first POC deliberately tackles only a narrow but representative slice of that vision. We will create several **simulated greenhouse environments**, including a primary greenhouse containing 40 cherry-tomato plants. Each greenhouse is represented as an independent entity in the platform.

The platform will allow a user to select a greenhouse, inspect its current state, and, for simulated greenhouses, explicitly run the simulation. The simulation will advance progressively through its timeline while observations, events, reconstructed plant states and operational insights appear in the interface.

Once a simulation has completed, its last simulated day becomes its current state. The user can then navigate backwards and forwards through the generated history.

A lightweight but functional **operations dashboard** will make this state observable. The user will be able to inspect the greenhouse spatially, select individual plants, inspect their reconstructed state and history, and understand how the greenhouse evolved.

The objective is not to accurately simulate tomato biology or construct a complete physical digital twin. Instead, the POC should demonstrate how heterogeneous temporal observations and events can be transformed into a coherent, explainable and queryable representation of greenhouse reality.

---

# 2. Core Product Model

The platform manages **greenhouses**.

A greenhouse is independent from the mechanism through which its data is produced.

Conceptually:

```text
Platform
   │
   ├── Greenhouse A
   │      source: SIMULATION
   │
   ├── Greenhouse B
   │      source: SIMULATION
   │
   └── Greenhouse C
          source: LIVE
```

For the POC, all available greenhouses will be simulations.

However, the domain model should avoid assuming that every greenhouse is simulated.

A greenhouse may eventually receive observations from:

```text
SIMULATION
REAL_SENSORS
EXTERNAL_API
IMPORTED_DATA
```

The intelligence layer should operate on observations and events without needing to know where they originated.

---

# 3. Why This Separation Matters

The simulation is a **data-generation mechanism**.

The greenhouse is a **domain entity**.

These concepts should remain separate.

A real greenhouse would continuously receive observations over time.

A simulated greenhouse instead produces those observations through a scenario engine.

Once observations and events have been created, both should pass through the same downstream architecture:

```text
           Real greenhouse
                 │
                 ▼
          observations/events
                 │
                 │
                 ▼
            STATE ENGINE
                 ▲
                 │
                 │
          observations/events
                 ▲
                 │
          Simulation engine
                 ▲
                 │
        Simulated greenhouse
```

This allows the POC architecture to remain relevant when real sensors are introduced later.

---

# 4. Why We Are Building This First

The difficult and reusable part of the larger greenhouse project is not necessarily physical automation.

Before connecting real cameras, sensors, irrigation systems or robots, we need to understand how the software should represent and reason about greenhouse reality.

In particular:

- What information should be retained for every plant?
- How should observations be represented over time?
- How do greenhouse-level and plant-level observations interact?
- How do we combine visual information with sensor measurements?
- How should known human or robotic interventions be represented?
- How do we infer an intervention when it was not explicitly reported?
- How do we distinguish natural development, intervention and anomalous observations?
- What belongs to deterministic computation?
- What requires higher-level reasoning?
- How should uncertainty and provenance be represented?
- How can recommendations be explained?
- How do we aggregate individual plant states into operational information?
- How can we reconstruct what the greenhouse looked like at any previous point in time?
- How should multiple greenhouses be represented?
- How can the same intelligence engine operate on simulated and eventually live greenhouse data?
- How can we evaluate whether the intelligence layer is behaving correctly?

The POC therefore focuses on:

```text
observations
    +
events
    ↓
longitudinal state
    ↓
derived information
    ↓
reasoning
    ↓
operational insights
    ↓
evaluation
```

---

# 5. POC Greenhouses

The platform should initially expose at least two greenhouse configurations.

## 5.1 Simulation Greenhouse 001

Primary demonstration greenhouse.

Example configuration:

```text
Name:
Simulation Greenhouse 001

Type:
SIMULATION

Crop:
Cherry tomatoes

Plants:
40

Duration:
28 simulated days

Layout:
4 rows × 10 plants
```

This is the main POC scenario and contains multiple interacting situations:

- normal growth;
- ripening;
- harvesting;
- water stress;
- heat events;
- recovery;
- hidden interventions;
- anomalous sensor measurements.

---

## 5.2 Simulation Greenhouse 002

A deliberately smaller scenario demonstrating that the architecture is configuration-driven rather than hard-coded for 40 plants.

For example:

```text
Name:
Longitudinal Plant Demo

Type:
SIMULATION

Crop:
Cherry tomato

Plants:
1

Duration:
40 simulated days
```

This scenario can focus more deeply on the history of a single plant.

It does not need the complexity of the primary simulation.

Its main purpose is to demonstrate that greenhouse size and simulation duration are configurable.

---

# 6. Greenhouse Domain Object

A greenhouse should conceptually contain:

```text
greenhouse_id
name
description

source_type

layout
plants

created_at

current_state_timestamp
latest_available_timestamp
```

For simulated greenhouses, additional metadata is available through a separate simulation configuration.

The core greenhouse model should not require simulation-specific fields.

---

# 7. Simulation Definition

A simulated greenhouse has an associated simulation definition.

Conceptually:

```text
simulation_id
greenhouse_id

scenario_definition
start_date
duration_days
step_duration

random_seed

status
current_step
total_steps
```

Possible statuses:

```text
NOT_STARTED
RUNNING
COMPLETED
FAILED
```

The simulation definition describes how observations and events will be generated.

It should remain separate from the greenhouse's reconstructed state.

---

# 8. Simulation Scenario

A simulation scenario defines the ground-truth evolution of the simulated environment.

It may include:

```text
environmental evolution

plant development

plant-specific scenarios

scheduled interventions

hidden interventions

sensor anomalies

visual changes
```

For example:

```text
Plant 17
Day 8–10:
normal fruit ripening

Day 11:
harvest recommended

Day 12:
hidden harvest

Day 13:
post-harvest development
```

The scenario represents **what actually happens in the simulated world**.

The intelligence system does not have direct access to the full scenario definition.

---

# 9. Fundamental Domain Principle

The greenhouse is a **changing system**.

The state of a plant at time `T` is not simply its latest sensor reading.

It is the result of:

```text
previous state
+
natural evolution
+
environment
+
new observations
+
known interventions
+
inferred interventions
```

Therefore, the central abstraction of the project is a **longitudinal plant state**.

---

# 10. Observation, Event and State

The system must explicitly distinguish three concepts.

## 10.1 Observation

An observation represents something measured or detected.

Examples:

```text
soil moisture = 38%
air temperature = 31.2°C
visible fruit count = 47
ripe fruit count = 12
wilting score = 0.31
```

Observations are evidence.

They should remain immutable historical records.

---

## 10.2 Event

An event represents something that happened.

Examples:

```text
plant watered
fruit harvested
plant pruned
fertiliser applied
manual inspection performed
plant removed
```

Events may be explicitly reported or inferred.

Potential sources include:

```text
HUMAN_REPORTED
ROBOT_CONFIRMED
CONTROL_SYSTEM
INFERRED_FROM_OBSERVATIONS
SIMULATION
```

---

## 10.3 State

State represents the system's current interpretation of reality after reconciling observations, previous state and events.

Example:

```text
Plant 17

development stage:
fruiting

estimated visible fruit:
47

estimated ripe fruit:
12

estimated ripe mass:
620 g

health:
healthy

water stress:
mild

lifetime harvested:
2.8 kg

last intervention:
watering, 31h ago

next expected harvest:
1–2 days
```

The state is therefore derived.

It should not simply duplicate the latest observation.

---

# 11. Provenance

Derived information should retain provenance whenever useful.

A fact may be:

```text
OBSERVED
REPORTED
DETERMINISTICALLY_DERIVED
INFERRED
```

For inferred information, confidence should also be available.

Example:

```text
last_harvest:
    timestamp: 2026-08-25T10:15
    estimated_mass_kg: 0.82
    provenance: INFERRED
    confidence: 0.94
```

---

# 12. Complete Conceptual System

```text
                    PLATFORM
                       │
              Greenhouse Registry
                       │
           ┌───────────┴───────────┐
           │                       │
      Simulated                Real / Live
      greenhouse               greenhouse
           │                       │
    Simulation Engine              │
           │                       │
           └───────────┬───────────┘
                       │
                 OBSERVATIONS
                       +
                  KNOWN EVENTS
                       │
                       ▼
             LONGITUDINAL STATE ENGINE
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    Temporal       State-change     Event
    features       reconciliation   inference
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
               INTELLIGENCE LAYER
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      Alerts      Recommendations   Forecasts
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
               OPERATIONS PLATFORM
```

---

# 13. Scope of This POC

```text
       GREENHOUSE REGISTRY
               │
               ▼
       Select greenhouse
               │
               ▼
       Simulated greenhouse
               │
               ▼
        Simulation engine
               │
      progressive execution
               │
               ▼
     observations + events
               │
               ▼
       temporal persistence
               │
               ▼
    longitudinal state engine
               │
               ▼
      derived information
               │
               ▼
       reasoning workflow
               │
               ▼
 insights / recommendations
               │
               ▼
          dashboard
               │
               ▼
          evaluation
```

---

# 14. Explicitly Out of Scope

## Real Computer Vision

No raw image processing, training, segmentation or detection.

The POC consumes structured visual features.

## Accurate Biological Simulation

The simulator exists to exercise software behaviour, not reproduce tomato biology scientifically.

## Full Physical Digital Twin

No 3D geometry, branch topology or robot reachability.

## Robotics

No robot control or motion planning.

## Physical Control

No pumps, valves, windows, fans or irrigation hardware.

## Natural-Language Greenhouse Assistant

Explicitly reserved for Future Work.

## Production Infrastructure

No multi-tenancy, Kubernetes, billing, production authentication or complex access control.

---

# 15. Greenhouse Spatial Model

Each plant has a stable physical position.

At minimum:

```text
plant_id
row
position_in_row
```

Optionally:

```text
x
y
zone
tray_id
```

Example:

```json
{
  "plant_id": "plant_017",
  "variety": "cherry_tomato",
  "row": 2,
  "position_in_row": 7,
  "x": 6.0,
  "y": 2.0
}
```

The frontend should derive the greenhouse schematic from this configuration.

---

# 16. Future Spatial Hierarchy

The architecture should allow a producer to eventually represent:

```text
Producer
  │
  ├── Site
  │     │
  │     ├── Greenhouse A
  │     │      ├── Zone A1
  │     │      └── Zone A2
  │     │
  │     └── Greenhouse B
  │
  └── Site 2
```

This hierarchy is not implemented in the POC.

However, the current `greenhouse_id` boundary should make such expansion straightforward.

---

# 17. Environmental Observations

Initial greenhouse-level measurements:

```text
timestamp
air_temperature_c
relative_humidity_pct
```

Potential later additions:

```text
light_level
external_temperature
CO2 concentration
```

---

# 18. Plant-Level Sensor Observations

Initial plant-level data:

```text
plant_id
timestamp
soil_moisture_pct
```

Potential future measurements:

```text
soil_temperature
substrate_EC
substrate_pH
```

---

# 19. Visual Observations

Example:

```json
{
  "plant_id": "plant_017",
  "timestamp": "2026-08-24T12:00:00Z",

  "leaf_wilting_score": 0.18,
  "leaf_discoloration_score": 0.05,

  "visible_fruit_count": 47,
  "green_fruit_count": 24,
  "ripening_fruit_count": 11,
  "ripe_fruit_count": 12,

  "average_fruit_diameter_mm": 19.2,
  "estimated_visible_fruit_mass_g": 1880,

  "flower_count": 7
}
```

These values represent the output of a hypothetical future vision system.

---

# 20. Operational Events

Initial event types:

```text
WATERING
HARVEST
PRUNING
FERTILISATION
MANUAL_INSPECTION
```

Example:

```json
{
  "event_id": "evt_00392",
  "plant_id": "plant_017",
  "timestamp": "2026-08-25T10:15:00Z",
  "event_type": "HARVEST",
  "source": "HUMAN_REPORTED",
  "confidence": 1.0,
  "parameters": {
    "estimated_mass_g": 820
  }
}
```

---

# 21. Temporal State

Historical state is a first-class concept.

The platform should answer:

```text
What does Plant 17 look like now?
```

and:

```text
What did Plant 17 look like on Day 8?
```

through the same underlying state model.

Materialised state snapshots are acceptable for this POC.

---

# 22. State Reconstruction

For every simulation step:

```text
previous state
      +
new observations
      +
known events
      ↓
derived temporal features
      ↓
state-change analysis
      ↓
event reconciliation / inference
      ↓
new state
```

---

# 23. Event Reconciliation and Missing Events

Known interventions should be reconciled with observed changes.

Hidden interventions should sometimes be inferred.

Example:

```text
Day 12:
18 ripe fruits

Harvest happens internally in simulation.

No HARVEST event is exposed.

Day 13:
2 ripe fruits
plant structure otherwise stable
```

Expected inference:

```text
Probable harvest
confidence: high
```

---

# 24. Derived Features

Examples:

```text
soil_moisture_24h_delta
soil_moisture_3d_trend

temperature_max_24h
hours_above_temperature_threshold

wilting_change_24h

fruit_count_change
ripe_fruit_count_change
estimated_ripe_mass

hours_since_last_watering
hours_since_last_harvest

lifetime_harvest_mass
```

---

# 25. Hybrid Reasoning

Deterministic computation should be preferred whenever possible.

For example:

```text
ripe fruit count dropped by 16
```

is deterministic.

Interpretation such as:

```text
Was this most likely harvest, fruit loss,
measurement error or another event?
```

may involve higher-level reasoning.

---

# 26. Simulation Execution Model

A simulation should not necessarily be generated instantaneously before the user sees anything.

For demonstration purposes, the platform should support **progressive execution**.

Conceptually:

```text
Start simulation

Day 1
  generate observations
  generate events
  reconstruct state
  persist
  publish update

wait configurable delay

Day 2
  generate observations
  generate events
  reconstruct state
  persist
  publish update

...

Day 28
```

The default visible demo delay may be approximately:

```text
1 second per simulated day
```

The exact delay should be configurable.

---

# 27. Simulation Persistence

Simulation progress must be persisted.

If the application restarts after a completed simulation, opening that greenhouse should show:

```text
Simulation status:
COMPLETED

Current day:
28 / 28
```

The user should **not need to rerun it**.

Similarly, an interrupted simulation could potentially resume from its persisted position, although full resume support is optional for the first version.

---

# 28. Scenario Generation

The primary simulator generates:

```text
40 plants
×
28 days
×
daily state-changing observations
```

using a deterministic random seed.

The scenario includes:

- normal plants;
- stress scenarios;
- harvest events;
- hidden events;
- recovery;
- anomalies.

---

# 29. Ground Truth

The simulator retains private ground-truth metadata.

This information is not passed into the intelligence pipeline.

It exists solely for evaluation.

---

# 30. Evaluation

Evaluation should measure:

```text
issue detection
event inference
action recommendation
priority classification
false positives
evidence grounding
confidence calibration
state reconstruction consistency
```

Objective deterministic evaluation should be preferred whenever ground truth exists.

---

# 31. Operational Aggregation

Individual plant states should aggregate to greenhouse-level information:

```text
healthy plants
plants requiring attention
plants requiring immediate action

estimated ripe fruit mass
harvest completed today
cumulative harvest

open recommendations
```

Later versions can include workload forecasting.

---

# 32. Interface — Overall Product Flow

The user does **not** arrive directly inside a greenhouse.

The application starts with a **greenhouse selection interface**.

The basic product flow is:

```text
Open application
      ↓
Greenhouse list
      ↓
Select greenhouse
      ↓
Open greenhouse dashboard
      ↓
If simulation NOT_STARTED:
    offer Run Simulation
      ↓
Simulation progresses visually
      ↓
Simulation completes
      ↓
Current day = final simulated day
      ↓
Historical navigation available
```

For a real greenhouse, the equivalent flow would simply be:

```text
Open greenhouse
      ↓
Display current live state
```

There would be no `Run Simulation` action.

---

# 33. Greenhouse Selection Screen

The landing screen should display all available greenhouses.

Example:

```text
GREENHOUSES

┌────────────────────────────────────┐
│ Simulation Greenhouse 001          │
│                                    │
│ Cherry tomatoes                    │
│ 40 plants                          │
│ 28 simulated days                  │
│                                    │
│ Status: Completed                  │
│ Latest state: Day 28               │
│                                    │
│                         Open →     │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ Longitudinal Plant Demo            │
│                                    │
│ Cherry tomato                      │
│ 1 plant                            │
│ 40 simulated days                  │
│                                    │
│ Status: Not started                │
│                                    │
│                         Open →     │
└────────────────────────────────────┘
```

The greenhouse list is not simulation-specific.

A future live greenhouse might appear as:

```text
Greenhouse Paris 03

Cherry tomatoes
2,400 plants

Status:
Live

Last observation:
2 minutes ago
```

---

# 34. Greenhouse Dashboard States

The dashboard behaves differently depending on the greenhouse state.

## Simulation Not Started

The greenhouse layout is visible in its initial state.

Example:

```text
Simulation Greenhouse 001

Simulation not started

40 plants
Day 0 / 28

[ Run Simulation ]
```

All plants may initially appear in a neutral state.

The user can inspect the configured starting state.

---

## Simulation Running

Example:

```text
Simulation Greenhouse 001

Running simulation...

Day 8 / 28

████████░░░░░░░░░░░░  29%
```

The greenhouse map updates progressively.

The user sees:

- plants change operational status;
- fruit counts evolve;
- alerts appear;
- interventions occur;
- KPIs change.

The interface should feel like the greenhouse is evolving.

---

## Simulation Completed

Example:

```text
Simulation Greenhouse 001

Current state

Day 28 / 28
Simulation completed
```

Historical navigation is now fully available.

The dashboard initially opens on Day 28.

---

# 35. Progressive Simulation UI

Simulation execution should be visually observable.

At each step, the frontend receives the newly persisted greenhouse state.

Possible implementation mechanisms include:

```text
polling
Server-Sent Events
WebSocket
```

The exact mechanism is an implementation detail.

For the POC, simplicity is preferable.

The conceptual event is:

```text
simulation_step_completed
    greenhouse_id
    day
    total_days
    timestamp
```

The frontend then reloads or receives the corresponding dashboard state.

---

# 36. Main Dashboard Layout

```text
┌───────────────────────────────────────────────────────────────┐
│ ← Greenhouses     Simulation Greenhouse 001                  │
│                                                               │
│ Day 14 / 28                  Running...                       │
│ ██████████░░░░░░░░░░                                         │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ 40 plants | 34 healthy | 4 monitor | 2 action required       │
│ 3.8 kg ready | 1.2 kg harvested today                        │
│                                                               │
├─────────────────────────────────────┬─────────────────────────┤
│                                     │                         │
│          GREENHOUSE PLAN            │      PLANT DETAILS      │
│                                     │                         │
│    ● ● ● ● ● ● ● ● ● ●            │                         │
│                                     │                         │
│    ● ● ● ● ● ● ● ● ● ●            │                         │
│                                     │                         │
│    ● ● ● ● ● ● ● ● ● ●            │                         │
│                                     │                         │
│    ● ● ● ● ● ● ● ● ● ●            │                         │
│                                     │                         │
├─────────────────────────────────────┴─────────────────────────┤
│ Active insights / operational priorities                     │
└───────────────────────────────────────────────────────────────┘
```

---

# 37. Greenhouse Map

Each plant appears as a clickable element.

The map is generated from greenhouse configuration.

Plant statuses might be:

```text
HEALTHY
MONITOR
ACTION_REQUIRED
UNKNOWN
```

During simulation, status changes should immediately appear visually.

For example, a plant may progress:

```text
HEALTHY
   ↓
MONITOR
   ↓
ACTION_REQUIRED
   ↓
HEALTHY
```

The visual changes help make the temporal behaviour obvious during the demo.

---

# 38. Plant Selection

A user may select a plant at any point.

The detail panel displays the plant state for the currently displayed simulation day.

Example:

```text
Plant 17
Cherry tomato

POSITION
Row 2 · Position 7

CURRENT STATE
Health                  Healthy
Development             Fruiting
Water stress            Mild
Visible fruit           47
Ripe fruit              12
Estimated ripe mass     620 g
Lifetime harvested      2.8 kg

LATEST OBSERVATIONS
Soil moisture           43%
Temperature             27.1°C
Humidity                69%

LATEST EVENT
Harvest
Yesterday 10:14
780 g

ACTIVE INSIGHTS
Harvest recommended within 1–2 days
```

---

# 39. Plant History

The detail view exposes the history available up to the selected point.

Example:

```text
Day 8      Watered 700 ml
Day 9      5 ripe fruits
Day 10     8 ripe fruits
Day 11     Harvest recommended
Day 12     Probable harvest · inferred
Day 13     Normal development
```

---

# 40. Plant Charts

Useful charts include:

```text
soil moisture

temperature

green / ripening / ripe fruit count

estimated fruit mass

wilting / health score
```

When inspecting historical Day 12, charts should preferably display data only up to Day 12 or clearly distinguish future data.

The UI should not accidentally reveal future simulated information when viewing an earlier point.

---

# 41. Current Day During Simulation

While a simulation is running, the latest completed step is considered the current state.

For example:

```text
Simulation progress:
Day 11 / 28

Current state:
Day 11
```

The map and detail panel always correspond to that latest persisted state unless the user explicitly pauses to inspect history.

For the first implementation, historical navigation may remain disabled until simulation completion if that greatly simplifies UI behaviour.

---

# 42. Historical Navigation After Completion

Once simulation status becomes:

```text
COMPLETED
```

the final simulation day becomes the greenhouse's current state.

Example:

```text
Day 28 / 28
```

The user may then move backwards and forwards through the complete history.

Conceptually:

```text
Day 1 ── Day 2 ── Day 3 ── ... ── Day 28
                                  ▲
                                NOW
```

---

# 43. Time Travel Behaviour

Selecting a historical day updates the whole dashboard consistently.

This includes:

- greenhouse KPIs;
- plant map statuses;
- selected plant state;
- fruit counts;
- cumulative harvest as of that date;
- recent events;
- recommendations;
- charts;
- operational priorities.

Example:

```text
Day 10

Plant 17:
21 ripe fruits
1.15 kg ready
Recommendation: Harvest
```

then:

```text
Day 11

Plant 17:
3 ripe fruits
160 g ready
Probable harvest inferred
```

---

# 44. Return to Current State

Historical mode should clearly indicate that the user is viewing the past.

Example:

```text
Viewing Day 14

Current state is Day 28

[ Return to Current Day ]
```

This distinction will also make sense later for real greenhouses.

---

# 45. Greenhouse Switching

A greenhouse selector should remain easily accessible.

For example:

```text
← Greenhouses
```

or a dropdown:

```text
Simulation Greenhouse 001 ▼
```

The user can switch between available greenhouse environments without restarting the application.

Each greenhouse maintains its own:

```text
plants
history
observations
events
simulation status
current state
recommendations
```

---

# 46. API / Application Boundary

Conceptual endpoints may include:

```text
GET /greenhouses

GET /greenhouses/{greenhouse_id}

GET /greenhouses/{greenhouse_id}/state

GET /greenhouses/{greenhouse_id}/state?day=14

GET /greenhouses/{greenhouse_id}/timeline

GET /greenhouses/{greenhouse_id}/plants/{plant_id}

GET /greenhouses/{greenhouse_id}/plants/{plant_id}/history
```

Simulation-specific actions should remain separate:

```text
POST /simulations/{simulation_id}/run

GET /simulations/{simulation_id}/status
```

This distinction is important.

The generic greenhouse API does not need to know that a greenhouse is simulated.

---

# 47. Persistence Model

At a conceptual level, persisted data may include:

```text
greenhouses

plants

simulation_definitions

simulation_runs

observations

events

plant_state_snapshots

greenhouse_state_snapshots

recommendations

ground_truth
```

Ground truth belongs to simulation/evaluation and should not leak into normal application queries.

---

# 48. Logical Code Boundaries

```text
domain/
    greenhouse
    plants
    observations
    events
    state
    recommendations

simulation/
    definitions
    scenarios
    runner
    plant evolution
    environmental evolution
    intervention generation
    ground truth

intelligence/
    feature extraction
    state reconstruction
    event reconciliation
    event inference
    rules
    reasoning
    recommendations

evaluation/
    scenario evaluation
    state consistency
    recommendation evaluation

application/
    persistence
    greenhouse service
    simulation service
    API

frontend/
    greenhouse selector
    greenhouse dashboard
    simulation controls
    greenhouse plan
    timeline
    plant inspector
    charts
    priorities
```

---

# 49. First End-to-End Deliverable

A successful implementation should demonstrate:

```text
1. Start application.

2. Open greenhouse selection screen.

3. Display at least two configured simulated greenhouses.

4. Open Simulation Greenhouse 001.

5. Display its initial Day 0 state.

6. Display Run Simulation.

7. Start the simulation.

8. Progress approximately one simulated day per second.

9. Persist every step.

10. Update the greenhouse map progressively.

11. Display evolving KPIs.

12. Allow plants to change operational state visually.

13. Generate observations and interventions.

14. Reconstruct longitudinal plant states.

15. Generate insights and recommendations.

16. Complete the 28-day simulation.

17. Persist the final state.

18. Open on Day 28 after completion or restart.

19. Select individual plants.

20. Inspect their state and history.

21. Navigate backwards through simulation history.

22. Navigate forwards again.

23. Return to the current/final day.

24. Return to greenhouse selection.

25. Open the second simulation.

26. Demonstrate that a different greenhouse structure and timeline work through the same application architecture.

27. Run the evaluation suite against simulation ground truth.
```

---

# 50. Definition of Done

The POC should feel like a **small working product**, rather than a static simulation script.

A reviewer should be able to:

1. open the application;
2. see available greenhouses;
3. choose the primary simulation;
4. start it;
5. watch the greenhouse evolve;
6. see plant statuses change;
7. observe KPIs and recommendations evolve;
8. inspect individual plants;
9. reach the final simulated day;
10. rewind the greenhouse;
11. follow a plant's history through time;
12. understand an intervention or inferred event;
13. switch to another greenhouse;
14. see that the platform architecture is not specific to a single simulation.

The project should demonstrate:

**multi-greenhouse domain modelling, longitudinal state reconstruction, temporal data processing, event reconciliation, reasoning, provenance, evaluation, explainability and usable product design.**

---

# 51. Future Work — Natural-Language Greenhouse Analytics

A conversational interface could eventually allow users to ask questions about the selected greenhouse.

Examples:

```text
How many tomatoes did we harvest last week?

Which plants have experienced repeated water stress?

Which plants should someone inspect today?

How much harvest should we expect over the next three days?

Which greenhouse currently requires the most work?

Which row produced the most tomatoes?

Why does Plant 17 require attention?
```

The assistant should answer questions about greenhouse data rather than application source code.

---

# 52. Future Multi-Greenhouse Analytics

Once several real greenhouses exist, analytics may operate above a single greenhouse.

Examples:

```text
Which greenhouse has the largest expected harvest tomorrow?

Where do we need additional labour this week?

Which sites have recurring irrigation problems?

Which greenhouse has the highest disease risk?
```

This creates a future hierarchy:

```text
Organisation
      ↓
Sites
      ↓
Greenhouses
      ↓
Zones
      ↓
Plants
```

The current POC implements only the:

```text
Greenhouse
    ↓
Plant
```

portion.

---

# 53. Future Chat Architecture

```text
User question
      ↓
Selected greenhouse context
      ↓
Question interpretation
      ↓
Structured query generation
      ↓
SQL / application query
      ↓
Query execution
      ↓
Result validation
      ↓
Grounded natural-language answer
```

Queries should be constrained by the greenhouse or scope currently selected by the user.

---

# 54. Future Chat Evaluation

Because simulation data is controlled, many natural-language questions have deterministic ground truth.

Example:

```text
Question:
How much did Simulation Greenhouse 001
harvest between Day 8 and Day 14?

Ground truth:
18.42 kg
```

Evaluation may include:

```text
query correctness
result correctness
numeric correctness
grounding
answer quality
```

Deterministic evaluation should precede LLM-as-judge evaluation.

---

# 55. Future Real Greenhouses

A real greenhouse should eventually appear in exactly the same greenhouse selector.

The primary difference is its data source.

Example:

```text
Greenhouse Perche 01

Source:
LIVE

Plants:
1,200

Current state:
Aug 27 · 14:32

Last sensor update:
18 seconds ago
```

There is no:

```text
Run Simulation
```

button.

Instead, new observations continuously update the latest state.

Historical navigation behaves similarly to the simulated case.

This shared interface is one of the reasons simulation-specific concepts should remain separated from core greenhouse concepts.

---

# 56. Implementation Principle

The project should resist unnecessary complexity.

Recommended implementation order:

```text
Greenhouse domain model
        ↓
Simulation definition
        ↓
Persistence
        ↓
Greenhouse selection UI
        ↓
Simulation runner
        ↓
Progressive UI updates
        ↓
Plant/state reconstruction
        ↓
Dashboard
        ↓
Historical navigation
        ↓
Derived features
        ↓
Evaluation
        ↓
Reasoning / event inference
        ↓
Operational recommendations
```

Do not begin with an agent framework.

The first important milestone should already allow:

```text
Select greenhouse
      ↓
Run simulation
      ↓
Watch plants evolve
      ↓
Persist state
      ↓
Reopen at final state
      ↓
Navigate through history
```

Only after this backbone exists should increasingly sophisticated intelligence be added.

The goal is to build a small but coherent platform capable of **representing multiple greenhouse environments, observing their evolution, maintaining trustworthy longitudinal state, exposing that state through an operational interface, reasoning about changes, and evaluating whether those conclusions are correct.**
