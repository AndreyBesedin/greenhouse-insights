# Greenhouse Insights

Greenhouse Insights is an experimental project for **understanding and operating physical production systems through longitudinal data**.

The greenhouse is the first domain because it is accessible enough to instrument and simulate end to end, while still exposing the problems that make physical systems interesting: noisy observations, incomplete state, delayed consequences, uncertain interventions, operational trade-offs, and the need to connect recommendations back to real-world outcomes.

The long-term idea is simple:

```text
observe a physical system
        ↓
reconstruct its evolving state
        ↓
understand history and uncertainty
        ↓
identify useful actions
        ↓
human / software / robot executes
        ↓
observe the consequences
```

The current repository is a proof of concept for that loop. It is deliberately much narrower than the long-term vision.

## Why a greenhouse?

A greenhouse is a useful experimental environment because the sensing layer can initially be controlled: sensors can be selected deliberately, observations can be normalized, and the physical environment can eventually be instrumented directly.

That makes it possible to focus first on the reusable questions:

- How should a physical production system be represented over time?
- How do heterogeneous observations become coherent state?
- How should provenance and uncertainty be preserved?
- How do we separate observation, inference, policy, validation and execution?
- How do we evaluate whether a recommendation was actually useful?
- How do human and automated actions become part of the same history?

This is an important current assumption, not a solved problem. A future deployment based on existing or third-party sensing infrastructure would have a much harder ingestion and normalization problem.

## Current experiment

The current implementation uses simulated tomato greenhouses to explore the software architecture before introducing real hardware.

```text
Hidden simulated world
        ↓
Noisy observations
        ↓
Observable plant / greenhouse state
        ↓
Management policy or agent
        ↓
Recommendations
        ↓
Human approval / dismissal
        ↓
Deterministic validation + execution
        ↓
Next simulated day
        ↓
Evaluation against hidden truth
```

The agent never sees simulator-hidden ground truth and never mutates the greenhouse directly.

Today the POC includes:

- configurable greenhouses and a causal day-by-day tomato simulator;
- persistent plant, truss, fruit, environmental and operational history;
- noisy sensor and vision-like observations generated from hidden state;
- reconstructed observable state separated from simulation ground truth;
- deterministic and agentic management policies;
- recommendations for watering, harvesting, lowering plants and inspections;
- human review before agent recommendations affect the world;
- manual operator actions through the same validation/execution boundary;
- historical navigation and recommendation provenance;
- deterministic evaluation against simulator ground truth;
- a React + TypeScript frontend and Python + FastAPI backend.

## What this is not

This is not yet a production greenhouse product, a scientifically calibrated crop model, or an autonomous control system.

Current simplifications include:

- simulated observations instead of real cameras and sensors;
- simplified tomato biology and greenhouse physics;
- no detailed disease model or spatial climate model;
- no production actuator or robot integration;
- a single-process application architecture;
- human-reviewed management rather than autonomous control;
- no production authentication or multi-tenant organisation model.

## Milestones

The project is evolving roughly along the following path:

### 1. Represent the system

Create a persistent longitudinal model of greenhouses, plants, observations, events and actions without coupling the domain model to simulation.

**Status:** implemented in the current POC.

### 2. Build a controllable world model

Use a deterministic-but-probabilistic simulator to generate coherent histories and hidden ground truth for testing state reconstruction and decision policies.

**Status:** implemented, intentionally simplified.

### 3. Add operational decision support

Generate reviewable recommendations from observable state, keep reasoning and provenance inspectable, validate requested actions deterministically, and evaluate decisions against known outcomes.

**Status:** first implementation exists; evaluation remains basic.

### 4. Connect real observations

Feed real environmental sensors and plant observations into the same observable-state interface while preserving uncertainty and provenance.

**Status:** not implemented.

### 5. Learn from real operations

Use longer histories to improve forecasting, anomaly / disease detection, workload planning, policy evaluation and operator decision support.

**Status:** exploratory.

### 6. Close more of the loop

Allow irrigation systems, external software, automation or robots to consume validated actions, while keeping the same observation → state → policy → action architecture.

**Status:** future direction.

## Open questions

Some of the questions this project is intended to explore are still deliberately unresolved:

- How much state should be directly observed versus inferred?
- How should confidence and disagreement between sensors, vision and history be represented?
- What remains transferable when moving from controlled sensors to heterogeneous existing infrastructure?
- Which recommendations are worth automating and which should remain human decisions?
- What is the right evaluation horizon: immediate action correctness, plant health, yield, labour efficiency, or economics?
- How much of the system should be crop-specific versus reusable across physical production environments?
- When does a simulator remain useful once enough real-world data exists?

## Repository guide

The documentation is intentionally split between the current project view and historical design documents:

- [`docs/README.md`](docs/README.md) — documentation map and status of the design documents;
- [`docs/technical_reference.md`](docs/technical_reference.md) — current implementation and architecture reference;
- [`docs/design/greenhouse_intelligence_poc_brief.md`](docs/design/greenhouse_intelligence_poc_brief.md) — original product / POC framing;
- [`docs/design/greenhouse_simulation_design.md`](docs/design/greenhouse_simulation_design.md) — simulator design;
- [`docs/design/greenhouse_agentic_management_design.md`](docs/design/greenhouse_agentic_management_design.md) — management-policy and agent design;
- [`DEVELOPMENT_GUIDELINES.md`](DEVELOPMENT_GUIDELINES.md) — engineering conventions.

Some design documents describe intermediate decisions rather than the exact current application. They are kept because the decision history is useful.

## Running locally

Requirements:

- Python 3.12+
- Poetry 2.0+
- Node 22+ (`frontend/.nvmrc`)

### Backend

```bash
cd backend
poetry install
cp .env.example .env
poetry run uvicorn application.api.main:app --reload
```

API: `http://localhost:8000`

The default SQLite database is created automatically at `backend/data/greenhouse.db`.

### Frontend

```bash
cd frontend
nvm use   # or: nvm install
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### Agent provider

The default provider is deterministic and requires no external API.

To run agentic greenhouses against Anthropic instead:

```bash
GREENHOUSE_AGENT_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
```

Put these values in `backend/.env` or export them in the environment. See `backend/.env.example` for optional model, timeout, retry and token settings.

## Tests and evaluation

```bash
# backend
cd backend
poetry run pytest

# frontend
cd ../frontend
npm test

# repository-wide checks
cd ..
pre-commit run --all-files

# management evaluation
make backend-eval
```

If the backend API schema changes, regenerate the typed frontend client:

```bash
cd backend
poetry run python scripts/export_openapi.py ../frontend/openapi.json

cd ../frontend
npm run generate:api
```

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
```

This serves the frontend at `http://localhost:8080` and the API at `http://localhost:8000`.
