# Greenhouse Insights

A greenhouse intelligence and operational support platform POC. See
`docs/design/greenhouse_intelligence_poc_brief.md` for
the full product scope, `docs/design/` for all design documents, and
`DEVELOPMENT_GUIDELINES.md` for how this project is built.

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
`docs/design/greenhouse_agentic_management_design.md`. Decision-making lives
in `backend/management/`, separate from `backend/simulation/` (the world
model) - a greenhouse's `management_policy` (`NONE` / `DETERMINISTIC` /
`AGENTIC`) is resolved once per simulated day into a policy that only sees
observable state and proposes actions; validation and execution stay in
`simulation/`, which the policy never touches. The agent can call
`get_plant_state` / `get_plant_history` under a configurable tool-call
budget before finalizing its decision, and every agentic run is traced
(`GET /greenhouses/{id}/management/history`). `management/evaluation/`
holds 10 ground-truth decision-quality cases with a scorecard
(`python -m management.evaluation`). The agent runs against
`FakeAgentModelProvider` (scripted, no API calls) by default, or against a
real Claude model via `AnthropicAgentModelProvider` when configured - see
`GREENHOUSE_AGENT_PROVIDER` below.

## Running locally

Requires Python 3.12+ and Node 22+ (see `frontend/.nvmrc`).

**Backend:**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in any values you need to override, see below
uvicorn application.api.main:app --reload
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
# with the backend venv active
python backend/scripts/export_openapi.py frontend/openapi.json
cd frontend && npm run generate:api
```

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
cd frontend && npm test
```

`pre-commit run --all-files` runs the full lint/format/type-check/test suite
for both.
