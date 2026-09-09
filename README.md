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

The current implementation is one stage of that ongoing development path, not the final product.

## Why a greenhouse?

Greenhouses are a strong starting point because their core production asset — the plant — is still largely **unobservable over time**. Operators can measure aggregate outputs such as total harvest, climate conditions, irrigation or labour, but they typically do not have a reliable longitudinal record of each plant: how it has developed, what it has produced, whether it is degrading, what interventions it received, or what it is likely to produce next.

That creates a structural gap between **what is happening physically and what the operator can actually see and plan around**. Production is therefore managed with limited plant-level transparency, weak forecasting, and little ability to attribute outcomes to individual plants or interventions. Greenhouse Insights starts there: by turning plants from opaque physical assets into observable, longitudinal entities that can support better diagnosis, prediction, planning and eventually automation.

A greenhouse is also a useful experimental environment because the sensing layer can initially be controlled: sensors can be selected deliberately, observations can be normalized, and the physical environment can eventually be instrumented directly.

That makes it possible to focus first on the reusable questions:

- How should a physical production system be represented over time?
- How do heterogeneous observations become coherent state?
- How should provenance and uncertainty be preserved?
- How do we separate observation, inference, policy, validation and execution?
- How do we evaluate whether a recommendation was actually useful?
- How do human and automated actions become part of the same history?

This is an important current assumption, not a solved problem. A deployment based on existing or third-party sensing infrastructure would have a much harder ingestion and normalization problem.

## Current system

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

Today the project includes:

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

## What is intentionally simplified

The current system is not yet a production greenhouse platform, a scientifically calibrated crop model, or an autonomous control system.

Current simplifications include:

- simulated observations instead of real cameras and sensors;
- simplified tomato biology and greenhouse physics;
- no detailed disease model or spatial climate model;
- no production actuator or robot integration;
- a single-process application architecture;
- human-reviewed management rather than autonomous control;
- no production authentication or multi-tenant organisation model.

## Development path

### 1. Represent the system

Create a persistent longitudinal model of greenhouses, plants, observations, events and actions without coupling the domain model to simulation.

**Status:** implemented.

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

Some of the questions this project is intended to explore are deliberately unresolved:

- How much state should be directly observed versus inferred?
- How should confidence and disagreement between sensors, vision and history be represented?
- What remains transferable when moving from controlled sensors to heterogeneous existing infrastructure?
- Which recommendations are worth automating and which should remain human decisions?
- What is the right evaluation horizon: immediate action correctness, plant health, yield, labour efficiency, or economics?
- How much of the system should be crop-specific versus reusable across physical production environments?
- When does a simulator remain useful once enough real-world data exists?

## Repository guide

- [`docs/technical_reference.md`](docs/technical_reference.md) — current implementation and architecture reference;
- [`docs/archive/design-history/`](docs/archive/design-history/) — historical design and implementation-planning documents kept as decision history;
- [`DEVELOPMENT_GUIDELINES.md`](DEVELOPMENT_GUIDELINES.md) — engineering conventions.

The archived design documents describe intermediate decisions rather than the exact current application. They are kept because the decision history is useful; current code, tests, README and technical reference take precedence when they differ.

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

Backend tests:

```bash
cd backend
poetry run pytest
```

Frontend tests:

```bash
cd frontend
npm test
```

Run the repository-wide pre-commit checks:

```bash
pre-commit run --all-files
```

Run the management evaluation scorecard:

```bash
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

See [`docs/technical_reference.md`](docs/technical_reference.md) for persistence, deployment, provider, concurrency and architecture details.
