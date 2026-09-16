# 10 — Unified Greenhouse Interface and Temporal Decision Loop

Status: proposed implementation plan, 2026-09-16.

## Why this comes next

The project now has two useful worlds: a controllable simulator and WUR recorded greenhouse history. The backend is converging on source-independent observations and state, but the frontend still forks by source: simulated greenhouses use the operational dashboard and spatial plant map while imported WUR data use a dedicated recorded dashboard and measurement tables.

That split was useful while the WUR vertical slice was being built, but it is not the product model we want. Simulation, recorded replay and live operation should expose one greenhouse interface and one temporal decision loop. The source changes what is known and what can happen next; it should not create a different application.

Simulation remains a permanent first-class source even with large live deployments. As its biological and physical model improves it can support counterfactual experiments, hypothesis testing, policy evaluation, synthetic failure cases and training environments for RL or other control policies.

## Core principle

Greenhouse Insights operates on the same loop regardless of source:

```text
observations -> reconstructed state -> policy/recommendations -> action -> subsequent observations
```

The temporal world determines the action semantics:

- **Simulation:** recommendations can be reviewed and executed into a generated future. Counterfactual actions are possible.
- **Recorded replay:** recommendations can be generated and reviewed at a historical cursor, but cannot alter history. They are compared with recorded actions and subsequent outcomes.
- **Live:** recommendations can be reviewed and passed to a human/controller when supported; the future is not yet known and outcomes arrive later.

The UI should therefore branch on explicit capabilities, not on `source_type`.

## Goals

1. One `GreenhouseDashboard` composition for simulation, recorded replay and future live sources.
2. One timeline/cursor model based on timestamps/checkpoints rather than simulation-specific days.
3. One representation of observable entities, with graceful degradation when identity or geometry is unknown.
4. One recommendation/review experience with capability-dependent actions.
5. Make recorded replay useful for offline policy analysis: compare what the policy suggested at T with what was recorded after T.
6. Keep source-specific ingestion and execution adapters outside the domain/UI core.
7. Preserve simulation as a first-class controllable world, not a temporary demo fixture.

## Non-goals for this slice

- Proving that a historical alternative action would causally have produced a better outcome.
- Building a realistic greenhouse world model or RL training system now.
- Inventing plant identity or geometry absent from a dataset.
- Making WUR-specific measurements generic when they are genuinely dataset-specific.
- Implementing autonomous live actuation.
- Replacing the existing ingestion plans.

## 1. Capabilities instead of source-specific UX

Introduce a small capability description derived by the application layer from the greenhouse/world configuration. Example shape, not a committed API:

```text
can_advance_generated_time
can_execute_actions
can_review_recommendations
can_compare_with_recorded_actions
has_known_future
has_persistent_entity_identity
spatial_resolution
```

The frontend renders affordances from these capabilities. It must not accumulate conditions such as `source_type === 'IMPORTED_DATA'` to decide which dashboard exists.

A source type remains valuable provenance. It is not a UI mode.

## 2. Unified temporal model

The dashboard has a cursor at timestamp/checkpoint T.

At T it shows:

- observations available up to T;
- reconstructed state as known at T;
- provenance/confidence;
- recommendations produced using only information available at T;
- actions recorded or executed after the recommendation, where available;
- subsequent outcomes only when the user intentionally moves beyond T or enters analysis mode.

This temporal honesty is essential for replay evaluation: a policy evaluated at T must not receive future WUR observations.

The same timeline supports three meanings of "next":

- simulation: generate the next state after validated actions;
- replay: reveal the next recorded checkpoint;
- live: wait for/receive the next observations.

The controls may differ, but the timeline and state presentation do not.

## 3. Observable entities and spatial uncertainty

The UI must not assume that every source has persistent plants at exact row/position coordinates.

Represent what is actually known. A future domain shape may distinguish:

- greenhouse;
- compartment/zone;
- persistent plant;
- crop/sample entity;
- sensor/media observation with a spatial reference.

Spatial knowledge should be explicit rather than fabricated. Suggested levels:

- `EXACT_OR_STRUCTURED`: known row/position or physical coordinate;
- `GROUP_ONLY`: known compartment/treatment/zone but no trustworthy within-group geometry;
- `UNKNOWN`: no useful placement.

Rendering degrades accordingly:

```text
structured geometry     Row 1   o o o o o
                        Row 2   o o o o o

group only              Compartment 3.06
                        [sample] [sample] [sample]

unknown                 observed entities / measurements
                        without fake placement
```

The current simulation map can become one renderer of the common entity collection. The current WUR table remains useful as a detail/measurement view, not as a separate greenhouse application.

## 4. Unified entity detail

Selecting an entity opens the same conceptual panel:

- identity/type and spatial knowledge;
- current reconstructed state;
- latest observations and provenance;
- history up to the current cursor;
- recommendations concerning the entity;
- recorded/executed actions where available;
- outcomes after those actions when analysis permits them.

Fields may be absent. Absence should be represented as unknown/not observed, not filled with simulation assumptions.

## 5. Unified recommendation UX

A recommendation is a policy output against state at T. Its presentation should be the same across worlds.

### Simulation

```text
Recommendation: WATER zone A
[Approve] [Dismiss]
```

Approval may execute into the simulated world.

### Replay

```text
Recommendation at T: increase ventilation
Historical action: ventilation remained unchanged
Outcome +2 h: RH increased to ...
[Compare with history]
```

There is no execute operation because history is immutable. Review may still be allowed as annotation/evaluation, but it cannot mutate the recorded trajectory.

### Live

```text
Recommendation: inspect row 7
[Approve / assign / dismiss]   # only when supported by the live execution boundary
```

The recommendation model should not encode these world-specific mechanics. Execution/comparison belongs to the temporal environment around it.

## 6. Replay policy analysis

Recorded WUR history should become an offline evaluation environment rather than only a dataset viewer.

At historical cursor T:

1. reconstruct state using observations available at or before T;
2. run a baseline/policy against that state;
3. persist the recommendation with policy version and evidence/provenance;
4. inspect the recorded controls/actions in a defined future window;
5. classify agreement/disagreement where a meaningful mapping exists;
6. expose subsequent observed outcomes;
7. aggregate cases for later policy evaluation.

Example:

```text
T                  policy: increase ventilation
T -> T+10 min      recorded control: unchanged
T+2 h              observed RH: 91%
classification     policy/history disagreement
```

This is evidence for post-hoc analysis, not proof of a counterfactual. The system must distinguish:

- **policy/history agreement**;
- **recorded subsequent outcome**;
- **counterfactual estimate** (only when a validated model supports one).

Never label a recommendation "correct" solely because the historical trajectory later deteriorated.

## 7. Simulation's long-term role

Simulation is a permanent execution environment behind the same interfaces.

Near term it provides deterministic/controlled tests, hidden truth, failure injection and counterfactual action execution. Longer term, increasingly realistic biological and physical models can support:

- testing agronomic/control hypotheses before field trials;
- comparing policies under matched initial conditions;
- generating rare/failure scenarios;
- sensitivity analysis;
- model-based planning;
- RL training/evaluation environments;
- testing safety constraints before live execution.

The unified interface is important precisely because a policy should be able to move from simulation -> historical replay -> shadow live -> controlled live operation without being rewritten around a new application model.

## 8. Proposed frontend direction

Replace the top-level source fork in `GreenhouseDashboardPage` over time:

```text
GreenhouseDashboard
  Timeline
  Context / capability banner
  EnvironmentSummary
  EntityView
    SpatialEntityMap | GroupedEntityView | EntityList
  EntityDetail
  RecommendationPanel
  Action / ReplayComparisonPanel
```

Source-specific components may exist for specialized data, but they are children/plugins of the common dashboard. `RecordedGreenhouseDashboard` should eventually disappear as a top-level alternate application.

The context banner should clearly state the world semantics, for example:

- `Simulation · generated future · actions executable`
- `Recorded replay · history immutable · policy analysis`
- `Live · observations current as of 14:32 · human execution`

## 9. Backend/application boundaries

Keep these concepts separate:

- **Observation/state domain:** source-independent facts and reconstructed knowledge.
- **Policy:** consumes only observable state at T and emits recommendations.
- **Temporal environment:** simulation, replay or live chronology/capabilities.
- **Execution adapter:** applies approved actions where execution is possible.
- **Replay comparator:** maps policy recommendations to recorded actions/controls and later outcomes without mutating history.
- **Provenance:** records where observations/actions came from.

Avoid a generic mega-interface prematurely. Implement the smallest common contracts proven by both simulation and WUR; add live requirements when ThingSpeak/professional live data lands.

## 10. Implementation sequence

Each step should be a small PR where practical.

### 10.1 — Characterize the existing split

- Add/adjust frontend tests that pin the useful behaviours of simulation and WUR dashboards.
- List source-specific assumptions in `GreenhouseDashboardPage`, `RecordedGreenhouseDashboard`, `GreenhouseMap`, `RecordedPlants`, timeline hooks and recommendation hooks.
- Do not change UX yet.

### 10.2 — Introduce explicit world capabilities

- Add the minimal application/API capability model required by simulation and recorded replay.
- Derive capabilities server-side from configured world/source semantics.
- Add generated-schema/frontend coverage.
- No source-type checks for top-level UX decisions after this step unless they are strictly provenance labels.

### 10.3 — Common timeline and dashboard shell

- Move header, source/capability banner, timeline, state timestamp and common summaries into one dashboard composition.
- Preserve simulation controls and recorded immutability through capabilities.
- Keep specialized WUR panels intact inside the common shell.

### 10.4 — Common observable-entity view

- Define the minimum entity/spatial metadata needed by current simulation and WUR data.
- Reuse the spatial plant map when structured geometry is trustworthy.
- Add grouped/list rendering when only compartment/treatment or no geometry is known.
- Move WUR measurement table into entity detail/secondary analysis rather than making it the primary greenhouse representation.

### 10.5 — Common entity detail and recommendation presentation

- One selection/detail flow across sources.
- One recommendation card/panel.
- Capability-aware actions: execute/review in simulation; non-mutating review/analysis in replay.

### 10.6 — First replay policy comparison

- Choose one recommendation/control pair with defensible semantics in WUR rather than trying to map every control.
- Run policy at T with strict no-future leakage.
- Show policy recommendation, recorded action/control and subsequent outcome side by side.
- Persist enough policy/version/context metadata for reproducibility.
- Add tests proving recorded history cannot be mutated and future data cannot leak into policy input.

### 10.7 — Extract only proven common abstractions

After simulation + WUR work through the same UI and temporal loop, remove obsolete recorded-dashboard code and duplicated hooks. Do not generalize further for hypothetical live sources yet.

## 11. Definition of done

This plan is complete when:

- simulation and WUR open the same top-level dashboard;
- the UI does not select an alternate dashboard from `source_type`;
- both use one timestamp/checkpoint timeline abstraction;
- observable entities share one selection/detail model and do not invent unavailable geometry/identity;
- recommendations have one presentation model;
- simulation can still review/execute actions and advance generated time;
- replay cannot mutate history;
- at least one WUR replay case compares a policy recommendation at T with recorded behaviour and a later observed outcome;
- tests prove no future leakage in replay policy evaluation;
- specialized source panels are optional children of the common interface rather than alternate applications;
- simulation remains independently runnable and suitable for future model/RL work.

## 12. Relationship to other plans

- `wur_real_data_ingestion_replay_plan.md` defines the recorded-data architecture and WUR source semantics. This plan builds the common product/decision interface on top of that work.
- `wur_execution_plan.md` remains the active execution record for infrastructure and WUR ingestion tasks already underway.
- PR #8's ThingSpeak plan should be implemented after the common interface boundary is established enough that a live source does not create a third dashboard. ThingSpeak should plug into the same observation/timeline interface and initially remain read-only.
- `infrastructure_update_plan.md` and `authentication_authorization_plan.md` are orthogonal platform plans and should not be renumbered retroactively merely for cosmetics.
