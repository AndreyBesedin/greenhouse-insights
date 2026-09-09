# Domain model and evaluation refactor plan

Temporary planning document for the post-review refactor. The goal is to preserve the current `main` branch exactly as reviewed while preparing a small stack of focused PRs that clarify the domain model, make evaluation cases reflect states the real pipeline can actually produce, and then archive obsolete planning material once the work is complete.

This is intentionally a design/refactor plan, not a mandate to merge everything before the technical discussion.

## Why this refactor

Three concerns surfaced while reviewing the current code and evaluation suite:

1. Simulation context has leaked into domain objects that should also be valid for a real greenhouse.
2. `PlantHealth`, plant observations, environmental measurements, and reconstructed state are too entangled. In particular, health is currently inferred directly from soil moisture, although the intended meaning is closer to the plant's own condition than to a single environmental reading.
3. Some policy evals manually construct `PlantState` objects that are syntactically valid but cannot be emitted by the real observation -> reconstruction pipeline.

The cleanup should happen as a stacked set of PRs so each architectural change can be reviewed independently and the exact version Jean reviewed remains available on `main`.

---

# PR 1 — Separate simulation context from greenhouse domain identity

**Suggested branch:** `refactor/simulation-context-boundary`
**Base:** `main`

## Goal

Make simulation an execution/data-source context rather than an intrinsic part of greenhouse domain entities.

A greenhouse, plant, observation, state snapshot, event, or recommendation should conceptually remain valid whether its data came from a simulator, physical sensor, vision pipeline, human operator, or another future ingestion source.

Simulation-specific objects should still carry `simulation_id` where the run is genuinely their identity or execution scope.

## Approach

Inventory every model/table containing `simulation_id` and classify each occurrence as one of:

- domain identity;
- execution context;
- provenance;
- persistence/query metadata.

Keep `simulation_id` on simulation definitions, simulation progress/status, runner/orchestration objects, and traces whose actual scope is one simulation run.

Revisit it on generic greenhouse-domain records such as `Observation`, state snapshots, events, recommendations, and similar objects that should also exist in live operation.

Prefer explicit provenance where appropriate. Conceptually:

```python
Observation(
    observation_id="obs_123",
    greenhouse_id="gh_1",
    plant_id="plant_3",
    source=ObservationSource(
        type="SIMULATION",
        source_id="sim_123",
    ),
    ...
)
```

The same source model should later support `SOIL_SENSOR`, `VISION_PIPELINE`, `HUMAN`, etc.

The conceptual relationship should be:

```text
SimulationRun -> produces domain data
```

rather than:

```text
Domain data -> must belong to a simulation
```

It is acceptable for persistence tables to retain a simulation/run foreign key when useful for querying, as long as this is treated as persistence/execution metadata rather than intrinsic domain identity.

Also remove brittle assumptions such as deriving a simulation id from a greenhouse id (`sim_{greenhouse_id}`) where practical.

## Acceptance criteria

- Generic greenhouse-domain types do not require a simulation concept unless they genuinely represent a simulation-specific operation.
- Simulation-produced data remains traceable to the run that produced it.
- Existing demo behavior remains unchanged.
- One greenhouse can conceptually support multiple simulation runs and live data without changing its identity.
- No broad persistence redesign purely for architectural purity.

---

# PR 2 — Separate observations, environment, plant condition, and reconstructed state

**Suggested branch:** `refactor/state-model-separation`
**Base:** `refactor/simulation-context-boundary`

## Goal

Clarify what each piece of state means so environmental measurements are not conflated with plant health.

Desired conceptual flow:

```text
raw / derived observations
        |
        v
environment state + plant observations
        |
        v
reconstructed plant state
        |
        +--> plant condition / health assessment
```

## Domain intent

### Observation

A measured or observed fact at a point in time: soil moisture, visible/ripe fruit counts, estimated ripe mass, visible height, visual symptoms, temperature, humidity, etc. Observations should carry source/provenance.

### Environment state

The reconstructed environment around a plant/zone/greenhouse: soil moisture, air temperature, humidity, and future environmental values. This is not plant health.

### Plant state

The reconstructed operational state of the plant: development/size, fruit state, relevant environmental context, last action/event, and plant condition.

### Plant health / condition

The plant's own condition rather than whether one environmental variable crossed a threshold. Future evidence could include disease/damage, wilting/stress symptoms, longitudinal deterioration, anomalies across observations, or prolonged environmental stress.

For this POC the model should remain simple. The important semantic change is that low soil moisture may trigger an operational action without automatically meaning that the plant itself is unhealthy.

## Reconstruction behavior

`reconstruct_plant_state` should remain the normal path from observations/events to the state consumed by management policies. Split it into smaller functions only when that improves semantics, for example:

```text
reconstruct_environment_state(...)
assess_plant_condition(...)
reconstruct_plant_state(...)
```

Management thresholds should read from the correct source of truth: environment, plant condition, or both.

## Acceptance criteria

- Soil moisture is represented as environment/observation data, not as the definition of plant health.
- Plant health/condition has a clear documented meaning.
- Management policies retain access to all information needed for decisions.
- Reconstruction is deterministic for a fixed observation/event set.
- No attempt to build realistic agronomy, disease simulation, advanced physiology, or new UI features.

---

# PR 3 — Make eval cases reachable through the real pipeline

**Suggested branch:** `eval/reachable-system-states`
**Base:** `refactor/state-model-separation`

## Goal

Keep targeted policy evaluation, but stop constructing combinations of state that the real system cannot produce.

The suite should distinguish two levels.

### Level A — focused policy evals

Build the smallest realistic observable input and pass it through the same reconstruction path as the application:

```text
observations + visible history/events
        -> real reconstruction code
        -> PlantState / EnvironmentState
        -> management policy
        -> expected recommendation(s)
```

This keeps cases small while guaranteeing reachability.

### Level B — a few deterministic end-to-end scenario evals

Exercise the real simulator/observation path where useful:

```text
hidden world
   -> simulation transition
   -> noisy observations
   -> reconstruction
   -> management policy
   -> recommendation
   -> evaluator compares with expected outcome / hidden truth
```

Hidden truth remains evaluator-only and must never enter the agent context.

## Existing behaviors to preserve

- low moisture can lead to watering;
- adequate moisture with no other trigger can lead to no action;
- ripe fruit can lead to harvest;
- excessive visible height can lead to lowering;
- independent triggers can produce multiple recommendations;
- ambiguous evidence can lead to inspection rather than a guessed intervention;
- history can change the decision;
- tool-budget exhaustion has a safe fallback.

## New semantic cases

Add at least:

1. **Low soil moisture, otherwise healthy plant** — watering may be needed while plant condition remains healthy.
2. **Plant health concern with adequate soil moisture** — inspection/monitoring can be needed for reasons unrelated to soil moisture.
3. **Longitudinal evidence changes the decision** — one noisy reading versus sustained evidence.
4. **One deterministic end-to-end simulator case** — fixed seed/config, real observations/reconstruction, expected recommendation class.

## Eval invariants

- policy input comes from reconstruction rather than arbitrary field combinations;
- history is ordered and belongs to the same plant;
- no future information is visible;
- hidden simulator truth never enters the agent context;
- expected actions respect the same validation constraints as the application.

## Acceptance criteria

- No eval relies on an unreachable state combination.
- Focused cases remain readable.
- At least one eval proves the environment/health distinction.
- At least one deterministic case covers simulator -> observation -> reconstruction -> decision.
- Existing provider comparison remains possible.

---

# PR 4 — Archive superseded design and implementation-planning documents

**Suggested branch:** `docs/archive-design-history`
**Base:** `eval/reachable-system-states`

## Goal

After the refactor and eval work is complete, clean the active documentation surface so current docs describe the current system, while preserving historical design documents as a trace of how the architecture evolved.

Do **not** perform this cleanup before PRs 1-3 are implemented. In particular, this planning document must stay where it is while it is still actively guiding the work.

## Archive policy

Create a folder such as:

```text
docs/archive/design-history/
```

Move into it design/planning documents that are no longer active specifications and may contain superseded decisions. Candidates should be reviewed at that time rather than moved blindly. Likely examples include:

- `demo_readiness_plan.md`;
- `greenhouse_agentic_management_design.md`;
- `greenhouse_intelligence_poc_brief.md`;
- `greenhouse_simulation_design.md`;
- `greenhouse_ui_initial_brief.md`;
- this `domain_model_eval_refactor_plan.md` once PRs 1-3 are complete.

Keep current reference documentation outside the archive, especially the README and `docs/technical_reference.md`, plus any design document that still accurately acts as a maintained specification.

Add a short `README.md` inside the archive explaining that:

- archived files are retained for decision traceability;
- they are historical snapshots, not current source-of-truth documentation;
- code, tests, README, and current technical reference take precedence when an archived document conflicts with the implemented system.

## Why keep rather than delete

The historical docs preserve rationale, trade-offs, and the sequence of decisions that led to the current architecture. That is useful for future reasoning even when the documents no longer describe the current implementation accurately.

Deletion is preferable only for files that contain no meaningful decision history or are pure duplication.

## Acceptance criteria

- Active documentation contains only material intended to describe or guide the current system.
- Superseded planning/design files are clearly isolated under an archive/history path.
- The archive is explicitly marked non-authoritative.
- This refactor plan is archived only after the refactor/eval stack is complete.
- No useful current reference documentation is moved merely because it is old.

---

# Stacking / review strategy

```text
main
  |
  +-- PR 1: refactor/simulation-context-boundary
        |
        +-- PR 2: refactor/state-model-separation
              |
              +-- PR 3: eval/reachable-system-states
                    |
                    +-- PR 4: docs/archive-design-history
```

Suggested review bases:

- PR 1 -> `main`
- PR 2 -> `refactor/simulation-context-boundary`
- PR 3 -> `refactor/state-model-separation`
- PR 4 -> `eval/reachable-system-states`

If the architectural direction changes during discussion, upper branches can be rebased or discarded without touching the reviewed version on `main`.

# What not to do before the discussion

- Do not merge the stack merely to make the repository look corrected.
- Do not hide the original eval issue.
- Do not archive the planning/design docs while they are still actively guiding implementation.
- Do not rewrite the simulator.
- Do not introduce a large provenance framework.
- Do not over-model plant biology.
- Do not chase a perfect model eval score.

# Recommended implementation order

1. Inventory and classify every `simulation_id` occurrence.
2. Introduce the smallest useful source/provenance model and remove clear simulation coupling from generic domain entities.
3. Separate environment, plant observations/state, and plant condition semantics.
4. Move management thresholds to their correct source of truth.
5. Rebuild policy eval inputs through real reconstruction.
6. Add the semantic and end-to-end eval cases.
7. Run unit tests, typing, lint, and provider evals for the stack.
8. Only once PRs 1-3 are complete, archive superseded design/planning docs in PR 4.
9. Keep all implementation PRs unmerged until after the technical discussion unless there is a strong reason to change that.
