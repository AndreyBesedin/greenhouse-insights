# Greenhouse Insights — Technical Reference

This document contains implementation details that are useful when developing, reviewing, or deploying the POC but are intentionally kept out of the main README.

For the original product intent and subsystem designs (archived, historical), see `docs/archive/design-history/`. For day-to-day engineering conventions, see `DEVELOPMENT_GUIDELINES.md`.

## Architecture

The central separation is:

```text
Hidden simulated world
        ↓
Noisy observations
        ↓
Observable greenhouse / plant state
        ↓
Management policy
        ↓
Requested actions / recommendations
        ↓
Human review
        ↓
Deterministic validation
        ↓
Action executor
        ↓
Updated hidden world
        ↓
Next simulated day
```

The major backend boundaries are:

- `simulation/` — hidden world state, biological/environmental evolution, observation generation, action execution.
- `management/` — deterministic and agentic decision policies. Policies only see observable state and never simulator-hidden truth.
- `intelligence/` — state reconstruction and interpretation of observations/events.
- `application/` — orchestration, persistence, API services, recommendation review workflow.
- `evaluation/` and `management/evaluation/` — deterministic checks against simulator ground truth.
- `domain/` — shared domain models and enums.

The frontend is React + TypeScript and consumes a generated client from FastAPI's OpenAPI schema.

## Manual simulation workflow

The primary demo/application flow is manual rather than autoplay:

1. Advance one simulated day.
2. Generate and persist noisy observations.
3. Reconstruct observable state.
4. Run the configured management policy.
5. Persist proposed actions as recommendations.
6. Let the operator approve or dismiss them.
7. Validate every approved action deterministically.
8. Execute accepted actions through the configured executor.
9. Reconstruct the current day's state from observations + executed events.
10. Advance again when the operator is ready.

Historical days remain read-only. Browsing history never rewinds or mutates the current hidden simulation world.

The legacy auto-run endpoint remains available for compatibility/testing, but the human-in-the-loop manual flow is the intended product/demo path.

## Recommendations and provenance

Agent output does not directly mutate the greenhouse.

A proposed action becomes a persisted `Recommendation` and goes through review. Current recommendation states are intentionally small: pending, dismissed, executed, or rejected by the deterministic validator.

The audit trail distinguishes the origin and execution path. Conceptually:

```text
source_policy = AGENTIC
approved_by = HUMAN
executed_by = SIMULATED_OPERATOR
```

Manual operator actions use the same execution and validation path and are persisted alongside agent recommendations so the event/audit history stays coherent.

## Agent providers

The management layer uses an `AgentModelProvider` abstraction.

### Fake provider

Default:

```bash
GREENHOUSE_AGENT_PROVIDER=fake
```

`FakeAgentModelProvider` is deterministic and makes no external API calls. It exists so the tool-calling workflow, recommendation pipeline, validation, persistence, UI, and evaluation remain reproducible without credentials.

### Anthropic provider

To use a real model:

```bash
GREENHOUSE_AGENT_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
```

Optional settings are documented in `backend/.env.example`, including model, timeout, retry, and max-token configuration.

The application intentionally limits the size/duration of newly created agentic simulations because an agentic greenhouse can make one billed model call per simulated day. See `application/greenhouse_service.py` for the current limits.

## Agent progress

While a real agentic day is being analysed, the backend exposes high-level progress such as:

```text
Analysing greenhouse…
Inspecting plant_003…
Checking plant_003 history…
2 recommendations ready
```

These are workflow/tool-activity events, not chain-of-thought. The frontend currently polls the progress endpoint while a next-day request is in flight.

## Demo scenario

`Agentic Demo Greenhouse` is the recommended live-demo configuration.

It contains 6 plants over 15 simulated days and is tuned so ordinary simulator dynamics reach the principal management action types quickly enough for a live walkthrough. It is not a scripted sequence of outcomes: the demo still runs through the normal simulator dynamics with a fixed/configured scenario.

The larger example greenhouses remain useful for longitudinal and scale-oriented testing.

## Evaluation

The simulator retains hidden ground truth that is never exposed to the management policy. This allows decision quality to be tested deterministically.

Run:

```bash
make backend-eval
```

or from `backend/`:

```bash
poetry run python -m management.evaluation
```

The fake provider is deterministic and serves as a stable reference. A real provider is deliberately not tuned to force a perfect score: the evaluation harness is intended to reveal reasoning gaps rather than hide them.

## Persistence and migrations

Persistence uses SQLite + SQLAlchemy Core. Schema migrations use Alembic.

The default database path is:

```text
backend/data/greenhouse.db
```

Override it with `GREENHOUSE_DATABASE_URL`.

The application applies migrations on startup. When changing `application/persistence/schema.py`, create the matching Alembic migration. Migration drift is covered by tests.

A standalone `alembic` CLI invocation does not automatically load `backend/.env`; export `GREENHOUSE_DATABASE_URL` in the shell first when running manual migration commands against a non-default database.

## API and generated frontend client

FastAPI's OpenAPI document is the frontend/backend contract.

After backend API/schema changes:

```bash
cd backend
poetry run python scripts/export_openapi.py ../frontend/openapi.json

cd ../frontend
npm run generate:api
```

Do not hand-maintain duplicate request/response interfaces in the frontend when the generated schema can provide them.

## Docker / deployment notes

For a local production-like run:

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
```

The frontend is served on `http://localhost:8080` and the API on `http://localhost:8000` by default.

The SQLite database lives in a named Docker volume so it survives container restarts. `docker compose down -v` removes the volume and therefore wipes the persisted database.

`VITE_API_BASE_URL` is a Vite build-time value. If frontend and backend are deployed to separate origins, rebuild the frontend with the correct API base URL and configure `GREENHOUSE_ALLOWED_ORIGINS` on the backend accordingly.

## Concurrency / POC constraints

The application protects per-simulation read-modify-write operations with in-process async locks. This is appropriate for the current single-process POC/demo, but it is not a distributed locking strategy. A multi-worker or horizontally scaled deployment would need persistence-backed coordination / transactional concurrency control.

Management progress is also kept in process memory and is therefore intentionally POC-level rather than durable/distributed state.

## Development approach

The initial product and architecture were developed iteratively with ChatGPT as a design partner. Most implementation work was then carried out through Claude Code sessions, with the repository owner steering scope, reviewing decisions, testing the result, and iterating on the implementation. Recent commits retain Claude co-author/session metadata for transparency.
