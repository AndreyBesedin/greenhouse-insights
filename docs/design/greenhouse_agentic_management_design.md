# Greenhouse Agentic Management — Initial Design Document

## 1. Purpose

This document defines the first agentic-management layer that will sit above the greenhouse simulator.

It is intentionally approximate.

The immediate priority remains building a coherent simulator V0.

Once the simulator is stable, this management layer will be implemented as the next major step.

The goal is to demonstrate a reusable agentic workflow in which an assistant observes greenhouse state, investigates plants through tools, chooses constrained management actions, and applies those actions through a validated execution boundary.

This layer should also remain relevant to the long-term product.

---

# 2. Core Principle

The simulator is the environment.

The management policy is the controller.

The agent is one implementation of the management policy.

```text
Simulator
    ↓
Observable greenhouse state
    ↓
Management policy
    ↓
Requested actions
    ↓
Validation
    ↓
Execution
    ↓
Simulator
```

The simulator must not contain LLM-specific logic.

---

# 3. Initial Objective

The first agent should optimize for two broad objectives:

```text
1. keep plants healthy
2. improve timely harvesting / production
```

The agent should also avoid unnecessary interventions.

Workforce and labour optimization are deliberately deferred.

Possible future objectives:

```text
labour availability
operator workload
water efficiency
energy efficiency
quality
yield
cost
robot capacity
```

---

# 4. Management Frequency

The agent runs once per simulation step.

For the current simulator:

```text
1 simulation step = 1 day
```

Therefore:

```text
1 management cycle = 1 simulated day
```

The simulation waits for the management cycle to complete before advancing.

---

# 5. Agent Input Boundary

The agent must not receive hidden simulator truth.

It sees only production-compatible information.

Initial context should include greenhouse-level metadata and summary information.

Then the agent may inspect individual plants through tools.

This is preferable to dumping the complete 40-plant world state into one prompt.

---

# 6. Initial Greenhouse Context

The management cycle may begin with:

```text
greenhouse_id
greenhouse name
crop
plant count
current simulation day

temperature
humidity

greenhouse operational summary

plants requiring attention
harvest summary
recent actions
active alerts
```

The exact summary can evolve.

---

# 7. Plant-Level Read Tools

Initial read tools:

```text
get_plant_state(plant_id)

get_plant_history(
    plant_id,
    days
)
```

Potential helper tools:

```text
get_greenhouse_summary()

get_active_alerts()
```

These are useful but not mandatory if their data already exists in initial context.

---

# 8. Plant State Tool

Conceptual call:

```text
get_plant_state("plant_017")
```

Possible result:

```json
{
  "plant_id": "plant_017",
  "status": "monitor",
  "development_stage": "fruiting",
  "soil_moisture_pct": 31.2,
  "water_stress": "moderate",
  "wilting_score": 0.37,
  "visible_fruit_count": 42,
  "ripe_fruit_count": 16,
  "estimated_ripe_mass_g": 910,
  "last_watering_hours_ago": 29,
  "last_harvest_days_ago": 4
}
```

Values are derived from observable platform state, not simulator truth.

---

# 9. Plant History Tool

Conceptual call:

```text
get_plant_history(
    plant_id="plant_017",
    days=7
)
```

Possible result:

```text
Day 8
soil moisture 44%
6 ripe fruits

Day 9
soil moisture 38%
10 ripe fruits

Day 10
soil moisture 33%
14 ripe fruits

Day 11
soil moisture 31%
16 ripe fruits
wilting increasing
```

This allows temporal reasoning without placing all historical data in the initial prompt.

---

# 10. Initial Action Tools

V1 action set:

```text
water_plant
harvest_plant
lower_plant
schedule_inspection
```

Keep the set intentionally small.

---

# 11. Water Tool

Conceptual tool:

```text
water_plant(
    plant_id,
    amount_ml
)
```

The tool creates a requested management action.

It does not directly mutate hidden state.

---

# 12. Harvest Tool

Harvesting is plant-level.

Conceptual tool:

```text
harvest_plant(
    plant_id,
    target="ripe"
)
```

The simulator determines which eligible fruits are harvested.

The agent does not select individual fruits.

---

# 13. Lower Plant Tool

Conceptual tool:

```text
lower_plant(
    plant_id,
    amount_cm
)
```

Used when plant operational height requires management.

---

# 14. Inspection Tool

Conceptual tool:

```text
schedule_inspection(
    plant_id,
    reason
)
```

This provides a safe response when evidence is ambiguous.

It also models future human-in-the-loop operation.

---

# 15. Automatic Execution in the Simulation

For the POC, accepted agent actions are automatically executed.

Conceptual flow:

```text
Agent requests action
        ↓
Action validator
        ↓
Accepted
        ↓
Simulated operator implicitly accepts
        ↓
Simulator applies action
```

Every action must retain:

```text
source = AGENT
```

along with timestamps and parameters.

---

# 16. Future Human-in-the-Loop Flow

The same abstraction should support:

```text
Agent recommends action
        ↓
Human sees recommendation
        ↓
Approve / reject / modify
        ↓
Action execution
```

No architecture should assume automatic execution forever.

---

# 17. Future Automation / Robotics Flow

Later:

```text
Agent requests action
        ↓
Safety / operational policy
        ↓
Scheduler
        ↓
Robot / greenhouse actuator
        ↓
Execution confirmation
```

For this reason, use generic concepts such as:

```text
ManagementAction
RequestedAction
ActionResult
```

rather than:

```text
RobotCommand
```

---

# 18. Hard Constraints vs Prompt Policy

Use both.

## Hard constraints

Implemented in code.

Examples:

```text
plant must exist
water amount > 0
water amount <= configured maximum
lower amount within supported range
action supported by greenhouse
daily action limits
```

Hard constraints cannot be overridden by the model.

## Soft management policy

Provided to the agent as configuration / instructions.

Examples:

```text
avoid unnecessary watering
prefer harvest when sufficient ripe mass exists
inspect when evidence is conflicting
avoid repeated interventions without new evidence
```

This separation is intentional.

---

# 19. Action Validation

Conceptual architecture:

```text
Agent
    ↓
RequestedAction
    ↓
ActionValidator
    ├── accepted
    └── rejected
```

Rejected actions should produce a structured result.

Example:

```json
{
  "accepted": false,
  "reason": "water amount exceeds configured daily maximum"
}
```

The agent may be allowed to react to validation failures within its tool-call budget.

---

# 20. Management Policy Interface

Conceptual abstraction:

```python
class ManagementPolicy(Protocol):
    def decide(
        self,
        context: GreenhouseManagementContext,
    ) -> list[RequestedAction]:
        ...
```

Implementations:

```text
NoOpPolicy
DeterministicPolicy
AgenticPolicy
```

---

# 21. Deterministic Baseline

V1 should include a deterministic baseline.

Possible initial rules:

```text
if soil moisture < threshold:
    request watering

if estimated ripe mass > threshold:
    request harvest

if operational plant height > threshold:
    request lowering

if observations conflict strongly:
    schedule inspection
```

The baseline must use only the same observable data the agent receives.

It must not access simulator truth.

---

# 22. Why the Baseline Matters

The deterministic policy gives useful comparisons:

```text
No management
vs
Rule-based management
vs
Agent management
```

This makes the agentic implementation easier to evaluate and explain.

The goal is not necessarily for the LLM to beat deterministic rules immediately.

The goal is to demonstrate:

- tool use;
- temporal reasoning;
- constrained execution;
- ambiguity handling;
- observability;
- evaluation.

---

# 23. Agentic Workflow

Initial agent cycle:

```text
Receive greenhouse context
        ↓
Identify plants worth investigating
        ↓
Call plant-state / history tools
        ↓
Decide whether action is justified
        ↓
Call zero or more action tools
        ↓
Finish management cycle
```

The agent should be allowed to choose **no action**.

---

# 24. Tool-Call Budget

The first implementation should enforce a finite tool-call budget.

Suggested starting range:

```text
5–10 tool calls per simulated day
```

This prevents uncontrolled loops and keeps latency predictable.

Exact value should be configurable.

---

# 25. Initial Agent Behaviour

High-level role:

```text
You are a greenhouse operations assistant.

Your objectives are to:
- keep plants healthy;
- support timely harvesting;
- avoid unnecessary interventions.

You do not have access to true greenhouse state.
Use only the available observations, history, and tools.

When evidence is ambiguous, prefer inspection or no action.

Do not invent measurements or unavailable actions.
```

Exact prompt wording should be refined during implementation.

---

# 26. Management Policy Configuration

Agronomic operating preferences should be configurable separately from the system prompt.

Example:

```text
target soil moisture range
maximum water per plant per day
minimum ripe mass before harvest
maximum plant operational height
inspection thresholds
```

This makes the eventual product configurable for different growers and crops.

---

# 27. Provider Abstraction

The agent architecture should remain provider-independent.

Conceptual interface:

```python
class AgentModelProvider(Protocol):
    def run_agent(...):
        ...
```

Potential adapters:

```text
OpenAI direct API
AWS Bedrock
Google Cloud / Vertex AI
other providers
```

No provider should leak deeply into domain logic.

---

# 28. Initial Provider Choice

The implementation may start with whichever provider is easiest to use in the development environment.

Likely options:

```text
direct OpenAI API key
AWS Bedrock
GCP / Vertex AI
```

The initial POC does not have significant security requirements.

Credentials still must not be committed to source control.

Use environment configuration.

---

# 29. Agent Traces

The system should retain useful execution traces.

At minimum:

```text
management cycle started
tool calls
tool results
requested actions
accepted actions
rejected actions
final management outcome
latency
provider/model metadata
```

Do not persist or expose private chain-of-thought.

Persist structured execution facts.

---

# 30. UI Visibility

Agent execution should be visible during simulation.

This is especially important because model calls may introduce latency.

Example UI:

```text
Day 12 / 28

Analysing greenhouse...
Reviewing Plant 17...
Reviewing Plant 31...
Evaluating harvest opportunities...
2 actions selected...
Applying actions...
```

The goal is to make the workflow understandable without exposing hidden reasoning.

---

# 31. Streamed Agent Progress

Possible high-level events:

```text
management_started
greenhouse_review_started
plant_inspection_started
plant_inspection_completed
action_requested
action_accepted
action_rejected
management_completed
```

Example:

```json
{
  "type": "plant_inspection_started",
  "day": 12,
  "plant_id": "plant_017",
  "message": "Reviewing Plant 17"
}
```

---

# 32. What the UI Should Not Show

Do not expose:

- hidden chain-of-thought;
- raw internal reasoning tokens;
- provider-specific debug internals;
- hidden simulator ground truth.

Instead expose:

```text
tools used
plants inspected
actions selected
validation outcomes
concise action rationale if explicitly generated
```

---

# 33. Daily Management Trace Example

```text
Day 12

Management started

Reviewed greenhouse summary

Inspected Plant 17
- soil moisture low
- wilting increasing
- high fruit load

Requested:
Water Plant 17 · 700 ml

Accepted

Inspected Plant 24
- inconsistent moisture reading

Requested:
Schedule inspection · Plant 24

Accepted

Management completed
2 actions applied
```

This can be displayed in the UI and persisted as structured trace data.

---

# 34. Simulation Interaction

The agentic policy participates directly in the simulation run.

Conceptual day:

```text
world advances
    ↓
observations emitted
    ↓
observable state updated
    ↓
agent management begins
    ↓
tool calls / decisions
    ↓
actions validated
    ↓
actions applied
    ↓
state persisted
    ↓
next day
```

Agent latency pauses advancement to the next simulation step.

---

# 35. Basic Evaluation — V1

Evaluation begins when the agentic-management phase starts, not during simulator V0.

Keep the first evaluation small.

Initial goals:

```text
Did the agent choose an expected action?
Was the action parameter within an acceptable range?
Did the agent avoid clearly unnecessary actions?
```

---

# 36. Expected-Action Ground Truth

For selected evaluation situations, the simulator/evaluation layer may store private expected behaviour.

Example:

```json
{
  "plant_id": "plant_017",
  "day": 12,
  "expected_action": "WATER_PLANT",
  "acceptable_amount_ml": {
    "min": 500,
    "max": 900
  }
}
```

The agent does not see this.

---

# 37. Initial Evaluation Metrics

Possible metrics:

```text
action type accuracy
action parameter validity
unnecessary-action rate
missed-action rate
invalid tool-call rate
inspection appropriateness
```

Keep the initial metric set small.

---

# 38. Later Outcome Evaluation

Future evaluation may examine the consequences of management.

Examples:

```text
plant stress reduced
ripe fruit harvested before over-ripening
water consumption
yield retained
health trajectory
```

This is deliberately later.

The first agent phase does not need policy optimization.

---

# 39. Comparison Runs

Eventually run the same simulation configuration and random seed using:

```text
NoOpPolicy
DeterministicPolicy
AgenticPolicy
```

Then compare:

```text
actions
harvest
plant health
water usage
missed interventions
```

This provides a strong evaluation story.

---

# 40. Failure Handling

Initial behaviour should define what happens if the agent fails.

Possible policy:

```text
agent timeout / provider error
        ↓
record failure
        ↓
apply no agent action for that day
        ↓
continue simulation
```

Alternatively a deterministic fallback may later be used.

For V1, a no-action fallback is acceptable and easy to reason about.

---

# 41. Idempotency

Management execution should guard against accidental duplicate actions.

Useful identifiers:

```text
simulation_run_id
day
management_cycle_id
action_id
```

Repeated processing of the same cycle should not silently water or harvest twice.

---

# 42. Action Result Model

Each action execution should produce a structured result.

Conceptually:

```text
ActionResult
    action_id
    accepted
    applied
    rejection_reason
    source
    timestamp
    resulting_event_id
```

This result can feed:

- UI;
- history;
- evaluation;
- debugging.

---

# 43. Suggested Package Boundaries

```text
management/
    policy.py

    context/
        models.py
        builder.py

    deterministic/
        policy.py
        rules.py

    validation/
        validator.py
        constraints.py

    agent/
        policy.py
        prompt.py
        tools/
            read_tools.py
            action_tools.py
        providers/
            base.py
            openai.py
            bedrock.py
            vertex.py
        tracing.py

    evaluation/
        expected_actions.py
        metrics.py
```

Exact names may evolve.

---

# 44. API / Service Boundary

The application layer should expose management status separately from simulator internals.

Possible conceptual endpoints:

```text
GET /simulation-runs/:runId/status

GET /simulation-runs/:runId/management/current

GET /simulation-runs/:runId/management/history
```

Progress may also be streamed.

---

# 45. Reusable Production Architecture

The same management policy should later be usable against a real greenhouse.

Replace:

```text
simulated observations
```

with:

```text
real sensors
real vision
operator events
```

and replace simulation action execution with:

```text
human approval
task creation
robot scheduler
climate controller
```

The agent core remains conceptually similar.

---

# 46. Initial V1 Scope

Implement after simulator V0:

```text
GreenhouseManagementContext

ManagementPolicy interface

DeterministicPolicy

AgenticPolicy

get_plant_state

get_plant_history

water_plant

harvest_plant

lower_plant

schedule_inspection

ActionValidator

provider abstraction

one provider adapter

management traces

streamed UI progress

small deterministic evaluation set
```

---

# 47. Explicitly Out of Scope for V1

Do not implement yet:

- autonomous ventilation control;
- automatic heating control;
- fertilisation optimisation;
- pruning policy;
- disease treatment selection;
- worker scheduling;
- robot dispatch;
- multi-agent orchestration;
- long-horizon planning;
- reinforcement learning;
- self-modifying prompts;
- autonomous code execution;
- unrestricted SQL tools.

Keep the workflow small and interpretable.

---

# 48. Definition of Done — Agentic Management V1

A successful V1 should allow:

1. running the simulator with an agentic policy;
2. giving the agent greenhouse-level context;
3. allowing plant-level investigation through tools;
4. allowing zero or more management actions per day;
5. validating every action in deterministic code;
6. automatically applying accepted actions to the simulator;
7. preserving `source = AGENT`;
8. persisting tool and action traces;
9. showing high-level agent progress in the UI;
10. continuing the simulation after management completes;
11. comparing behaviour with a deterministic baseline;
12. running a small expected-action evaluation suite;
13. changing the underlying LLM provider without changing simulator/domain logic.

---

# 49. Final Design Principle

The first agent should not be impressive because it talks.

It should be impressive because it operates inside a constrained, stateful environment:

```text
observe
    ↓
investigate
    ↓
decide
    ↓
use explicit tools
    ↓
pass deterministic validation
    ↓
change the environment
    ↓
observe consequences later
```

That is the core agentic workflow this POC should demonstrate.
