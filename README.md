# Greenhouse Insights

A greenhouse intelligence and operational support platform POC. See
`Greenhouse Intelligence POC — Project & Implementation Brief.md` for the full
product scope, and `DEVELOPMENT_GUIDELINES.md` for how this project is built.

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

## Running locally

Requires Python 3.12+ and Node 22+ (see `frontend/.nvmrc`).

**Backend:**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn application.api.main:app --reload
```

Serves the API at `http://localhost:8000`. Set `GREENHOUSE_STEP_DELAY_SECONDS`
to control the simulated-day pace (default 1.0s/day) and
`GREENHOUSE_DATABASE_URL` to change where the SQLite file lives (default
`backend/data/greenhouse.db`, created on first run).

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
