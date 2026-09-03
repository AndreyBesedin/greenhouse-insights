# Greenhouse Insights

A greenhouse intelligence and operational support platform POC. See
`docs/design/greenhouse_intelligence_poc_brief.md` for
the full product scope, `docs/design/` for all design documents, and
`DEVELOPMENT_GUIDELINES.md` for how this project is built.

## What this demonstrates

This POC explores how an AI system can make operational recommendations from
imperfect longitudinal data while keeping actions observable, constrained and
evaluable:

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

The agent only ever sees noisy observations, never the hidden world; every
action it proposes still passes through a human and a deterministic
validator before it can touch that world; and because the hidden world stays
available to the eval harness (never to the agent), decision quality is
something you can measure, not just eyeball.

**What this deliberately does not build:** production agronomic accuracy,
detailed spatial climate modelling, disease simulation, additional crops,
robotics or robot planning, autonomous climate control, multi-agent
orchestration, a generic chatbot / natural-language analytics layer,
production authentication, or a from-scratch visual redesign. All valid
future directions; none of them change the engineering idea being
demonstrated here.

## Demo walkthrough

The fastest way to see the whole loop, once the backend and frontend are
both running (see **Running locally** below - no seeding needed, every
greenhouse mentioned here is created automatically on first backend
startup):

1. Open the frontend and pick **Agentic Demo Greenhouse** (badged
   "Recommended demo") - 6 plants, 15 simulated days, `AGENTIC` policy,
   tuned so it reaches every action type within about 9 days instead of the
   ~30-40 `Simulation Greenhouse 001` / `Longitudinal Plant Demo` need (see
   `backend/simulation/scenarios/greenhouse_demo.py`).
2. Click **Next day →**. The simulator advances one hidden day and the agent
   inspects the noisy, observable-only result - day 1 typically proposes a
   few `SCHEDULE_INSPECTION` recommendations for ambiguous soil-moisture
   readings.
3. Open a recommendation card to see the evidence/reason behind it, then
   **Approve** or **Dismiss** it. Approving runs the same deterministic
   validator any action goes through, then executes and refreshes the
   KPIs/plant state - nothing the agent proposes touches the world until a
   human approves it.
4. Keep clicking **Next day →**. Watering shows up almost immediately,
   lowering by around day 7, harvesting by around day 9.
5. Use the day slider to browse a past day - it is read-only (no
   Approve/Dismiss), since only the current day accepts review.
6. Run `make backend-eval` to print the agent decision-quality scorecard -
   10 ground-truth cases graded against expected outcomes the agent never
   sees.

Steps 2-4 run against `FakeAgentModelProvider` (scripted, free, deterministic)
by default. Set `GREENHOUSE_AGENT_PROVIDER=anthropic` and an
`ANTHROPIC_API_KEY` to run the same flow against a real Claude model instead
- the recommendation cards, validator, and provenance trail are unchanged
either way.

## Status

**Milestone 1 (Backbone) — complete.** The app supports the full flow: select
a greenhouse → run its simulation → watch it progress day-by-day (persisted
each step) → reach the final day → navigate backwards/forwards through
history → switch greenhouses. Both POC greenhouses work through the same,
config-driven architecture (`Simulation Greenhouse 001`: 40 plants / 28 days,
`Longitudinal Plant Demo`: 1 plant / 40 days).

State reconstruction is deliberately trivial for this milestone (latest
observation restatement + one health threshold) — real reasoning, event
inference, recommendations, and the evaluation harness are Milestone 2+, per
the build order in `DEVELOPMENT_GUIDELINES.md`.

**Simulation engine (V0) — implemented**, per
`docs/design/greenhouse_simulation_design.md`. The simulator now maintains a
real hidden world per greenhouse (plants, trusses, individual fruits with
growth/ripening curves, a soil-water reservoir and water stress) that evolves
day over day, rather than generating independent random values each day. A
built-in deterministic policy automatically waters, harvests, and lowers
plants once per simulated day through a validated action boundary
(`WATER_PLANT` / `HARVEST_PLANT` / `LOWER_PLANT` / `SCHEDULE_INSPECTION`), and
sensor/vision observations are derived from that hidden state with
configurable noise. This is what powers the harvest-mass KPIs on the
dashboard and per-plant detail panel. The full spatial climate model and
streamed progress events remain out of scope for now.

**Agentic management (V1) — implemented**, per
`docs/design/greenhouse_agentic_management_design.md`. Three separate
concerns, deliberately: `backend/simulation/` owns world state and never
decides anything; `backend/management/` owns decision-making (a greenhouse's
`management_policy` - `NONE` / `DETERMINISTIC` / `AGENTIC` - is resolved
once per simulated day into a policy that only sees observable state) and
only ever *proposes* actions, never touching the world directly; carrying an
accepted action out is a third, separate, swappable step
(`simulation/executor.py`'s `ActionExecutor`, selected per simulation via
`action_executor` - only `SIMULATED_OPERATOR`, instantaneous and complete,
exists today, but a future simulated-robot or real executor is a new enum
member plus one class, not a refactor). The agent can call `get_plant_state`
/ `get_plant_history` under a configurable tool-call budget before
finalizing its decision, and every agentic run is traced
(`GET /greenhouses/{id}/management/history`). `management/evaluation/` holds
10 ground-truth decision-quality cases with a scorecard
(`make backend-eval`, or directly: `python -m management.evaluation` from
`backend/`) - reproducible against whichever provider
`GREENHOUSE_AGENT_PROVIDER` currently selects. The agent runs against
`FakeAgentModelProvider` (scripted, no API calls, passes all 10 cases by
construction) by default, or against a real Claude model via
`AnthropicAgentModelProvider` when configured - see `GREENHOUSE_AGENT_PROVIDER`
below. The real provider scored 7/10 on this scorecard as of its last
recorded run; the failures were left as-is rather than tuned against, since
the point of the harness is catching real reasoning gaps, not chasing 100%.
Because an `AGENTIC` greenhouse makes one real, billed LLM call per simulated
day, `POST /greenhouses` rejects `duration_days` over 30 or `rows * columns`
over 25 for that policy (see `MAX_AGENTIC_DURATION_DAYS` /
`MAX_AGENTIC_PLANT_COUNT` in `application/greenhouse_service.py`); the
Anthropic provider itself also carries a request timeout, retry cap, and
max-tokens ceiling, all configurable
(`GREENHOUSE_AGENT_REQUEST_TIMEOUT_SECONDS` / `GREENHOUSE_AGENT_MAX_RETRIES` /
`GREENHOUSE_AGENT_MAX_TOKENS`, see `.env.example`).

## Running locally

Requires Python 3.12+, [Poetry](https://python-poetry.org/docs/#installation)
2.0+, and Node 22+ (see `frontend/.nvmrc`). Also see `make help` at the repo
root for shortcuts to everything below (`make backend-dev`, `make test`, ...).

**Backend:**

```bash
cd backend
poetry install                 # creates backend/.venv (poetry.toml sets in-project venvs)
cp .env.example .env   # fill in any values you need to override, see below
poetry run uvicorn application.api.main:app --reload
```

Serves the API at `http://localhost:8000`. The app loads `backend/.env`
automatically on startup if it exists (`.env` is gitignored - never commit
it; `.env.example` documents every variable). Everything in it can also be
set as a real environment variable instead, which always takes precedence.
Notable ones: `GREENHOUSE_STEP_DELAY_SECONDS` controls the simulated-day
pace (default 1.0s/day), `GREENHOUSE_DATABASE_URL` changes where the SQLite
file lives (default `backend/data/greenhouse.db`, created on first run).

To run `AGENTIC` greenhouses against a real Claude model instead of the
scripted `FakeAgentModelProvider`, set `GREENHOUSE_AGENT_PROVIDER=anthropic`
and `ANTHROPIC_API_KEY=<your key>` (get one at console.anthropic.com, and
set a spend limit there too). Optionally set `GREENHOUSE_AGENT_MODEL` to
override the model (default `claude-sonnet-5`). A bare `alembic` command run
from the CLI does not read `.env` - export `GREENHOUSE_DATABASE_URL` in your
shell first if you need it for a manual migration command.

**Frontend:**

```bash
cd frontend
nvm use   # or: nvm install
npm install
npm run dev
```

Serves the app at `http://localhost:5173`. If the backend's API surface
changes, regenerate the typed client:

```bash
cd backend && poetry run python scripts/export_openapi.py ../frontend/openapi.json
cd frontend && npm run generate:api
```

## Tests

```bash
cd backend && poetry run pytest
cd frontend && npm test
```

`pre-commit run --all-files` runs the full lint/format/type-check/test suite
for both. (The pre-commit hooks still `source .venv/bin/activate` directly -
that keeps working unchanged since `poetry.toml` makes Poetry create the
venv in-project at `backend/.venv`, same as before.)

## Running with Docker

```bash
cp backend/.env.example backend/.env   # fill in real values first
docker compose up -d --build
```

Serves the frontend at `http://localhost:8080` and the API at
`http://localhost:8000`, with the SQLite database persisted in a named
Docker volume (`greenhouse_data`) so it survives container restarts.
`docker compose down -v` also removes that volume, wiping the database.

The frontend image bakes `VITE_API_BASE_URL` in at build time (Vite env vars
are compile-time, not runtime) - `docker-compose.yml`'s default points it at
`http://localhost:8000` for local compose testing. Deploying the two images
to different hosts/domains means rebuilding the frontend image with
`--build-arg VITE_API_BASE_URL=https://your-real-api-domain` pointed at
wherever the backend actually ends up, and setting
`GREENHOUSE_ALLOWED_ORIGINS` on the backend to match the frontend's real
origin.
