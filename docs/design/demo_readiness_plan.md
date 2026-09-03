# Greenhouse Insights — Demo Readiness Plan

## 1. Purpose

This document is the implementation entry point for making the current POC presentation-ready.

The target is **not** to expand the simulator or turn the project into a finished greenhouse product. The target is to make the existing architecture immediately understandable and interactive during a short technical discussion.

The strongest demo story is:

> A changing physical system produces imperfect longitudinal data. An agent inspects that data through explicit tools, proposes constrained actions, a human can approve or dismiss them, deterministic code validates and executes accepted actions, and the consequences appear on the next simulated day.

This is intentionally a **human-in-the-loop operational assistant**, not a fully autonomous greenhouse.

---

## 2. Current State

The repository already contains most of the technical depth required for the demo:

- config-driven simulated greenhouses;
- hidden greenhouse world with plants, trusses and fruits;
- day-by-day biological evolution;
- water dynamics and harvest state;
- noisy observable sensor / vision state;
- persisted daily snapshots and history;
- management-policy abstraction;
- deterministic and agentic management policies;
- read tools such as plant state and plant history;
- validated management actions;
- separate action-execution abstraction;
- agent traces;
- deterministic evaluation cases;
- React frontend and greenhouse dashboard.

The main issue is therefore **demo orchestration and visibility**, not missing architectural depth.

The current simulation runner automatically loops to completion. The current daily flow also immediately validates and executes actions returned by the management policy. The demo flow below deliberately changes both behaviours.

---

## 3. Target Demo Interaction

The simulation becomes manually stepped.

```text
Current Day
    ↓
Generate / display observations
    ↓
Agent analyses greenhouse
    ↓
Agent proposes actions
    ↓
Human reviews recommendations
    ↓
Approve / dismiss individually or in groups
    ↓
Accepted actions pass deterministic validation
    ↓
Accepted actions execute
    ↓
Persist actions and decisions
    ↓
[ Next Day ]
    ↓
Simulator advances and consequences become visible
```

One click on **Next Day** advances exactly one simulation step.

For this POC:

```text
1 simulation step = 1 day
```

There should be no requirement to autoplay the entire 28-day simulation during the demo.

Historical days remain navigable and read-only.

---

## 4. Core UX Principle

The user should feel that they are **operating a greenhouse with an AI assistant**, rather than watching an AI operate a simulation.

Each current day should have three visually distinct phases:

1. **Observed state** — what the greenhouse currently looks like.
2. **Recommendations** — what the agent proposes and why.
3. **Executed actions** — what the human actually approved and what the system applied.

The UI should not expose model chain-of-thought. It should expose structured facts:

- which plants were inspected;
- which read tools were called;
- what recommendation was produced;
- concise evidence / rationale;
- whether the human approved or dismissed it;
- whether validation accepted or rejected it;
- whether execution succeeded.

---

## 5. Desired Recommendation UI

A recommendation should be a first-class object in the frontend rather than an implicit backend action.

Example:

```text
Plant 17 · Water

Soil moisture declined from 42% → 31% over 3 days.
Wilting is increasing.

Recommended: 700 ml

[ Water 700 ml ]   [ Dismiss ]
```

Harvest example:

```text
Plant 24 · Harvest

18 ripe fruits
Estimated ripe mass: 1.1 kg

[ Harvest ripe fruit ]   [ Dismiss ]
```

Inspection example:

```text
Plant 08 · Inspect

Recent moisture observations are inconsistent.
The available evidence is insufficient for an automatic intervention.

[ Schedule inspection ]   [ Dismiss ]
```

The third case is especially useful in the demo because it demonstrates that uncertainty can lead to an explicit human workflow rather than fabricated certainty.

---

## 6. Aggregate Actions

Avoid making the operator click through all plants one by one when several recommendations are equivalent.

Support optional grouped recommendations where useful.

Example:

```text
Harvest ready plants
5 plants · estimated 4.2 kg

[ Harvest all ]

▸ View plants
```

The backend should still persist individual domain actions per plant so history and evaluation remain precise.

Aggregate actions are a presentation / workflow convenience, not a new simulator primitive.

---

## 7. Action Provenance

The current model largely treats agent actions as `source = AGENT` because they are automatically executed.

Human approval requires a slightly richer provenance model.

Preferred conceptual fields:

```text
requested_by = AGENT
approved_by = HUMAN
executed_by = SIMULATED_OPERATOR
```

This distinction is useful beyond the demo.

Future possibilities include:

```text
requested_by = AGENT
approved_by = AUTOMATION_POLICY
executed_by = ROBOT
```

or:

```text
requested_by = HUMAN
approved_by = HUMAN
executed_by = SIMULATED_OPERATOR
```

Do not over-generalize the implementation initially. Add the minimum domain representation necessary to preserve these semantics cleanly.

---

## 8. Simulation Runner Refactor

### Current issue

`SimulationRunner.run_to_completion()` repeatedly calls `_run_one_day()` and sleeps between days.

`_run_one_day()` currently performs all of the following in one operation:

```text
advance world
→ generate observations
→ reconstruct observable state
→ management policy decides
→ validate actions
→ execute actions
→ persist observations/events/world/state
→ advance current_step
```

For the interactive flow these concerns need a clearer day lifecycle.

### Target lifecycle

Prefer an explicit current-day state machine or equivalent application-level orchestration.

Conceptually:

```text
READY_TO_ADVANCE
    ↓ Next Day
ADVANCING_WORLD
    ↓
ANALYSING
    ↓
AWAITING_REVIEW
    ↓ human approves/dismisses
READY_TO_ADVANCE
```

The exact enum names are flexible. Keep the minimum number of states needed by the UI.

### Important semantic decision

Advancing to Day N should produce Day N observations and recommendations, then stop.

The simulation does **not** advance to Day N+1 until the operator explicitly clicks Next Day.

Accepted actions on Day N alter the hidden world before Day N+1 is calculated, so their consequences appear naturally on the following day.

---

## 9. Recommended Backend Split

Do not rewrite the simulator itself.

Refactor orchestration around the existing simulation boundaries.

A useful conceptual split is:

```python
prepare_day(simulation_id) -> DayPreparationResult

propose_management(simulation_id, day) -> RecommendationSet

review_recommendation(recommendation_id, decision)

execute_approved_actions(simulation_id, day)

advance_to_next_day(simulation_id)
```

The actual API need not expose exactly these functions. The important part is separating:

```text
world evolution
management proposal
human decision
validation
execution
finalization
```

Do not let the frontend mutate simulator world state directly.

---

## 10. Recommendation Domain Model

Introduce a persisted recommendation / proposed-action representation if one does not already exist with the required semantics.

Suggested conceptual fields:

```text
recommendation_id
simulation_id
greenhouse_id
simulated_day
plant_id | null

action_type
parameters

source_policy
status

reason
evidence
confidence | optional

requested_at
reviewed_at | null
executed_at | null
```

Possible statuses:

```text
PENDING
APPROVED
DISMISSED
REJECTED_BY_VALIDATOR
EXECUTED
FAILED
```

Avoid adding statuses that have no immediate use.

`reason` should be concise and user-facing. It is not chain-of-thought.

`evidence` should preferably be structured enough to support display, e.g. recent moisture values or ripe-mass figures.

---

## 11. Agent Output Contract

The agent should **propose**, not execute.

Its final output should map into one or more recommendation objects.

The management-policy contract can still return requested actions internally, but the application layer must persist them as pending recommendations before execution.

The agent must continue to see only observable greenhouse state and tool results, never simulator-hidden ground truth.

The initial tool set stays intentionally small:

```text
get_plant_state
get_plant_history

water_plant
harvest_plant
lower_plant
schedule_inspection
```

For the human-in-the-loop flow, action tools should semantically create proposals rather than immediately mutate the world.

---

## 12. Manual Next-Day API

Add an endpoint that advances a simulation by exactly one day.

Example shape:

```text
POST /simulations/{simulation_id}/next-day
```

Expected behaviour:

- reject if simulation is completed;
- reject or return conflict if the current day is still being analysed;
- define an explicit policy for pending recommendations;
- advance only one step;
- run management analysis for the resulting current day;
- return or expose enough status for the frontend to refresh.

Recommended rule for pending recommendations:

> The user may advance without accepting recommendations, but every pending recommendation must first have an explicit outcome.

For the simplest UX, clicking **Next Day** while pending recommendations remain can ask the frontend to confirm **Continue and dismiss remaining recommendations**.

The backend should then persist those remaining recommendations as dismissed before advancing.

This avoids silently losing agent suggestions.

---

## 13. Recommendation Review API

Provide explicit review actions.

Possible endpoints:

```text
GET  /greenhouses/{greenhouse_id}/recommendations?day=N
POST /recommendations/{recommendation_id}/approve
POST /recommendations/{recommendation_id}/dismiss
```

Approval should trigger deterministic validation before execution.

Conceptually:

```text
approve
  ↓
validate against current world
  ↓
accepted → execute → EXECUTED
  ↓
rejected → REJECTED_BY_VALIDATOR
```

Never trust parameters merely because they came from the agent or UI.

---

## 14. Agent Progress Visibility

During analysis the UI should show high-level structured progress.

Examples:

```text
Analysing greenhouse…
Inspecting Plant 17…
Checking Plant 17 history…
Inspecting Plant 24…
Evaluating harvest opportunities…
3 recommendations ready
```

Do not expose hidden reasoning or chain-of-thought.

### Transport

Start with polling unless it visibly harms the demo.

The existing project guidelines already prefer polling before SSE.

Expose a current phase / progress payload through the simulation or management status API.

Potential fields:

```text
simulation_id
day
phase
message
plant_id | null
completed_tool_calls
recommendation_count
```

Only move to SSE if polling produces a poor experience with a real provider.

---

## 15. Frontend Day Controls

The greenhouse dashboard should make the simulation clock explicit.

Suggested pattern:

```text
← Previous Day        DAY 12 / 28        Next Day →
                         CURRENT
```

Behaviour:

- historical days: read-only;
- current day: recommendations and actions enabled;
- future days: inaccessible;
- during analysis: Next Day disabled;
- after simulation completion: no Next Day action.

The current historical navigation should remain intact.

Do not conflate **Previous Day** for viewing history with changing the current simulation state. Rewinding the UI must never rewind the simulation world.

---

## 16. Frontend Management Panel

Add a compact operational panel to the current-day dashboard.

Suggested sections:

```text
AI assistant
────────────
Analysis status

Recommendations
- pending recommendation cards

Today's actions
- approved / executed actions
- dismissed recommendations
```

Useful summary line:

```text
3 recommendations · 2 executed · 1 dismissed
```

The panel should be useful without dominating the greenhouse map.

---

## 17. Interesting Demo Scenario

Create or identify one deterministic seed/configuration that reliably creates a short, understandable story.

Do **not** script outcomes directly.

The behaviour should emerge from normal simulator dynamics plus seeded randomness.

Ideal run includes several of:

- declining moisture causing a watering recommendation;
- ripe fruit accumulation causing harvest recommendation;
- plant lowering recommendation;
- ambiguous/noisy evidence causing inspection rather than intervention;
- visible next-day consequence after accepting or dismissing an action.

The demo does not need all cases within the first few days if that would distort the simulator.

Once a useful seed is identified, document it as the recommended demo greenhouse / seed.

Add a regression test or lightweight scenario assertion so later simulator changes do not silently destroy the demonstration path.

---

## 18. Evaluation Presentation

The existing deterministic agent evaluation should be made easy to show.

Do not build a large analytics feature.

Minimum acceptable version:

```text
Agent Evaluation
────────────────────────
Cases                 10
Correct action       9/10
Valid parameters    10/10
Unnecessary actions     0
Missed interventions    1
```

This can initially remain CLI-based if it is clean and reproducible.

A tiny frontend presentation is optional and lower priority than the main interactive loop.

The core story is:

> Because the simulator owns hidden ground truth, management decisions can be evaluated deterministically instead of only judged by another LLM.

---

## 19. Policy Comparison — Optional / Deferred Decision

Do not block demo readiness on policy comparison.

The architecture already supports multiple policies, so a future demo extension can run the same greenhouse / seed using:

```text
NONE
DETERMINISTIC
AGENTIC
```

and compare outcomes such as:

```text
harvested mass
water consumption
missed interventions
unnecessary actions
inspection count
```

This is potentially powerful but should be implemented only if the core manual-day + human-review workflow is already polished.

Treat it as **P2 / optional** for now.

---

## 20. Demo-Focused README Section

Add a short section near the beginning of `README.md` once the interactive flow is complete.

Suggested framing:

> This POC explores how an AI system can make operational recommendations from imperfect longitudinal data while keeping actions observable, constrained and evaluable.

Include a small architecture diagram:

```text
Hidden simulated world
        ↓
Noisy observations
        ↓
Observable plant state
        ↓
Agent + read tools
        ↓
Recommendations
        ↓
Human approval / dismissal
        ↓
Deterministic validator
        ↓
Action executor
        ↓
Next simulated day
        ↓
Evaluation against hidden truth
```

Also add a brief **What this deliberately does not build** paragraph:

- production agronomic accuracy;
- advanced climate physics;
- robotics;
- autonomous execution without review;
- multi-agent orchestration.

The README should help a reviewer understand the project's engineering intent in under two minutes.

---

## 21. Implementation Order

Follow the project's existing small-commit discipline.

### Phase 1 — Manual simulation stepping

Goal: replace auto-run-to-completion as the primary UI workflow.

Tasks:

1. expose one-day runner operation as a public/testable simulation capability;
2. add application-service `next day` orchestration;
3. add `POST /simulations/{id}/next-day`;
4. preserve current state/history persistence;
5. adapt runner/service tests;
6. update frontend simulation controls to advance one day manually;
7. keep or remove autoplay only after the manual flow works end-to-end.

Definition of done:

> A user can open a not-started simulation, click Next Day repeatedly, and each click advances exactly one persisted day.

### Phase 2 — Persist recommendations instead of auto-executing agent actions

Tasks:

1. introduce recommendation/proposal persistence;
2. separate management proposal from execution in daily orchestration;
3. persist agent recommendations as `PENDING`;
4. add review endpoints;
5. approval → validator → executor;
6. dismissal → persisted dismissal;
7. enrich provenance with requested / approved / executed semantics;
8. tests for approval, dismissal, rejection and duplicate review.

Definition of done:

> Agentic management can produce recommendations without changing the world until the operator approves them.

### Phase 3 — Frontend recommendation workflow

Tasks:

1. current-day AI assistant panel;
2. recommendation cards;
3. approve buttons;
4. dismiss buttons;
5. Today's Actions history;
6. explicit pending-recommendation behaviour when advancing;
7. disable interaction in historical mode;
8. frontend tests for current vs historical day and review actions.

Definition of done:

> During a current day the operator can see, approve and dismiss agent recommendations and then manually advance.

### Phase 4 — Agent progress visibility

Tasks:

1. expose management phase/progress state;
2. record/emit structured tool-activity events suitable for UI display;
3. poll from frontend while analysis is running;
4. show plant inspection/tool activity and final recommendation count;
5. measure real-provider latency before considering SSE.

Definition of done:

> A real LLM call no longer looks like a frozen UI; the operator sees meaningful high-level progress until recommendations are ready.

### Phase 5 — Demo scenario

Tasks:

1. inspect deterministic seeds/configurations;
2. select one with a useful operational story;
3. ensure it uses ordinary simulator dynamics, not scripted outcomes;
4. add regression coverage for the core events that make the scenario useful;
5. identify it clearly in the greenhouse selection page if needed.

Definition of done:

> A fresh demo reliably reaches understandable watering/harvest/inspection decisions without waiting through dozens of irrelevant days.

### Phase 6 — Evaluation presentation

Tasks:

1. make current evaluation CLI output presentation-friendly;
2. ensure command is documented and reproducible;
3. optionally expose scorecard in UI only if inexpensive.

Definition of done:

> Evaluation can be shown in under one minute during a technical discussion.

### Phase 7 — README / demo guide

Tasks:

1. add demo-oriented project framing;
2. add architecture diagram;
3. add a short local-demo runbook;
4. state intentional non-goals;
5. document recommended demo seed / greenhouse;
6. optionally add screenshots only after UI is stable.

Definition of done:

> Someone opening the repository understands what to run, what to click, and what engineering decisions to inspect.

### Phase 8 — Policy comparison (optional)

Only start this after Phases 1–7 are solid.

---

## 22. Suggested Commit Sequence

Keep commits narrow. Example sequence:

```text
refactor: expose single simulation day runner
feat: add manual next-day simulation endpoint
feat: add manual day controls to greenhouse dashboard

domain: add management recommendation model
feat: persist pending agent recommendations
feat: add recommendation review endpoints
feat: execute human-approved recommendations
feat: show agent recommendations in dashboard

test: cover manual management review flow
feat: expose agent progress during daily analysis
feat: show management progress in dashboard

test: lock deterministic demo scenario
chore: polish agent evaluation scorecard
docs: add demo walkthrough to README
```

Adjust commit types to the conventions in `DEVELOPMENT_GUIDELINES.md`; avoid bundling the entire plan into one large change.

---

## 23. Testing Priorities

Do not weaken the existing determinism / ground-truth boundaries while changing orchestration.

Must-cover cases:

```text
next-day advances exactly one step
same seed + same approved actions → same result
historical navigation does not mutate world state
agent recommendation does not execute before approval
approved action executes once
repeated approval is idempotent / rejected safely
dismissed action never executes
invalid approved action is rejected by validator
pending recommendations are not silently lost
human provenance is persisted
agent never receives hidden world truth
final day cannot advance
```

Add one frontend end-to-end-ish component flow for:

```text
Next Day
→ analysis
→ recommendations
→ approve one
→ dismiss one
→ Next Day
→ observe updated current day
```

---

## 24. Non-Goals for This Demo Pass

Do not spend demo-readiness time on:

- more sophisticated plant biology;
- detailed spatial climate modelling;
- disease simulation;
- additional crops;
- robotics;
- robot planning;
- autonomous climate control;
- multi-agent orchestration;
- generic chatbot / natural-language analytics;
- production authentication;
- major infrastructure work;
- visual redesign unrelated to the operational workflow.

These can all be valid future directions, but they do not materially improve the current interview signal.

---

## 25. Recommended Demo Walkthrough

Target approximately 10 minutes.

### 1. Open greenhouse

Explain that this is a personal POC around greenhouse intelligence and operational decision support.

### 2. Advance one day

Click **Next Day**.

Show that the simulator produces new observable state from a hidden causal world.

### 3. Watch agent analysis

Show high-level tool activity while it inspects the greenhouse.

Explain that the agent sees only observable state, not simulator ground truth.

### 4. Review recommendations

Open one plant recommendation.

Show evidence/history used by the agent.

Approve one action and dismiss another if the scenario supports it.

### 5. Show validation / provenance

Explain:

```text
Agent proposes
→ human approves
→ deterministic validator checks
→ executor applies
```

The model never directly mutates world state.

### 6. Advance again

Click **Next Day** and show consequences of accepted / dismissed interventions.

Optionally rewind the UI to the previous day to show longitudinal history without rewinding simulation state.

### 7. Show evaluation

Run/show the deterministic decision-quality evaluation.

Explain that hidden simulator truth makes deterministic agent evaluation possible.

### 8. Architecture close

The greenhouse is the domain example. The reusable engineering idea is:

> probabilistic reasoning operates inside an observable, constrained, human-reviewable and testable workflow.

---

## 26. Demo Readiness Definition of Done

The project is ready to present when:

1. simulation advances manually one day at a time;
2. agent analysis happens once per new current day;
3. the frontend visibly shows analysis progress;
4. the agent produces persisted recommendations rather than silently executing them;
5. the operator can approve or dismiss recommendations;
6. approved actions still pass deterministic validation;
7. execution provenance distinguishes agent proposal, human approval and simulated execution;
8. accepted actions affect subsequent simulated days;
9. historical navigation remains read-only and coherent;
10. at least one deterministic scenario produces a useful demonstration story;
11. evaluation can be shown quickly;
12. README contains a short demo entry point and architecture explanation;
13. full simulator sophistication and policy comparison are explicitly not blockers.

At that point, stop adding features and rehearse the story.