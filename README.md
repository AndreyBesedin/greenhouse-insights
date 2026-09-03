# Greenhouse Insights

Greenhouse Insights is a proof of concept for **greenhouse intelligence and operational decision support**.

The project explores how software can turn imperfect longitudinal greenhouse data into useful, reviewable actions: sensors and vision-like observations are reconstructed into plant state, a management policy proposes interventions, a human reviews them, deterministic code validates accepted actions, and the consequences appear in later greenhouse state.

The greenhouse domain is useful because decisions have persistent consequences. The broader engineering goal is to explore **observable, constrained and evaluable agentic workflows**, rather than build another text-generation demo.

## How it works

```text
Hidden simulated world
        ↓
Noisy observations
        ↓
Observable plant state
        ↓
Management policy / agent + read tools
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

The agent never sees simulator-hidden ground truth and never mutates the greenhouse directly.

## Current application

The current POC supports:

- multiple configurable greenhouses;
- a causal day-by-day tomato greenhouse simulator with persistent plant, truss, fruit and water state;
- noisy sensor / vision-like observations derived from hidden simulation state;
- manual simulation progression — one click advances exactly one simulated day;
- historical navigation without rewinding the underlying simulation;
- deterministic and agentic management policies;
- agent tools for inspecting current plant state and recent history;
- recommendations for watering, harvesting, lowering plants and scheduling inspections;
- human approval / dismissal before agent recommendations can affect the world;
- manual operator actions through the same deterministic validation/execution path;
- high-level agent progress in the UI while a day is being analysed;
- persisted recommendation provenance and management traces;
- deterministic evaluation against simulator ground truth;
- a dedicated small **Agentic Demo Greenhouse** for a short live walkthrough.

The frontend is React + TypeScript. The backend is Python + FastAPI with SQLite/SQLAlchemy persistence and Alembic migrations.

## Quick demo

Start the backend and frontend, then open **Agentic Demo Greenhouse** (marked **Recommended demo**).

1. Click **Next day →** to generate the next day's greenhouse state.
2. Watch the AI assistant inspect observable data and produce recommendations.
3. Review the evidence on a recommendation and **Approve** or **Dismiss** it.
4. Optionally apply a manual action from the plant detail panel.
5. Advance another day to see the consequences of the chosen interventions.
6. Use the day navigator to inspect earlier, read-only greenhouse state.
7. Run `make backend-eval` to show the deterministic management-evaluation scorecard.

By default the application uses a deterministic fake agent provider, so the complete workflow runs without external credentials. A real Anthropic provider can be enabled through environment variables.

## What is intentionally simplified

This is an engineering POC, not an agronomic production model. Current simplifications include:

- simplified tomato biology and greenhouse physics;
- no detailed spatial climate model;
- no disease model;
- simulated observations instead of real cameras/sensors;
- a single-process application architecture;
- human-reviewed management rather than production-grade autonomous control;
- no real robot / actuator integration;
- no production authentication or multi-tenant organisation model.

## Possible next steps

The most interesting directions from here are:

- connect real greenhouse sensor and vision data to the same observable-state interface;
- improve state reconstruction and uncertainty handling;
- add disease / anomaly detection and operational forecasting;
- extend evaluation from action correctness to longer-term outcome quality;
- add labour planning and workload forecasting;
- support real human/automation/robot executors behind the existing action boundary;
- compare different management policies on identical greenhouse scenarios;
- expand from the current greenhouse-level POC toward sites, zones and multiple crop types.

More detailed architecture and implementation notes live in [`docs/technical_reference.md`](docs/technical_reference.md). Product and subsystem design documents are under [`docs/design/`](docs/design/), and engineering conventions are in [`DEVELOPMENT_GUIDELINES.md`](DEVELOPMENT_GUIDELINES.md).

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

### Real agent provider

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
