# Greenhouse Intelligence POC — Development Guidelines

This document defines how we build this project day to day. The product scope lives in
`docs/design/greenhouse_intelligence_poc_brief.md`; this doc is about *how* we write and
ship the code that implements it. See `docs/design/` for all design documents, currently:

- `docs/design/greenhouse_intelligence_poc_brief.md` — overall product scope and vision.
- `docs/design/greenhouse_simulation_design.md` — design of the simulation engine (hidden
  world model, observation generation, scenario evolution).
- `docs/design/greenhouse_agentic_management_design.md` — design of the agentic management
  layer (policy interface, agent tools, action validation, evaluation).
- `docs/design/greenhouse_ui_initial_brief.md` — initial brief for the frontend UI/UX.

---

## 1. Guiding Principles

- **Small commits.** Each commit should do one coherent thing and leave the repo in a
  working, tested state. Prefer many small commits over one large one — easier to review,
  bisect, and revert.
- **Test-driven where practical.** For domain logic, state reconstruction, event
  reconciliation/inference, and evaluation metrics: write the test (or at least the
  assertion you want to be true) before or alongside the implementation. For UI and glue
  code, tests can follow implementation more loosely — TDD is a strong default, not a
  religion.
- **Evaluation is a first-class citizen, not an afterthought.** We control the simulation,
  which means we control ground truth. Every intelligence feature (event inference, state
  reconstruction, recommendations) should ship with a deterministic evaluation check against
  that ground truth in the same commit or the next one — not "later."
- **Clean but fast, with guardrails.** Optimize for legible, small, well-named units and
  clear boundaries between `domain/`, `simulation/`, `intelligence/`, `evaluation/`,
  `application/`. Don't gold-plate. The "locks" that let us move fast without accumulating
  mess are: automated linting/formatting, type checking, pre-commit hooks, and CI — not
  manual review ceremony.
- **No premature architecture.** Follow the build order from the brief (§56): domain model
  → simulation → persistence → selection UI → simulation runner → progressive UI → state
  reconstruction → dashboard → historical navigation → derived features → evaluation →
  reasoning → recommendations. Don't build reasoning/recommendation machinery before the
  backbone (select → run → persist → replay) works end to end.

---

## 2. Stack & Repo Layout

Monorepo, single git repository:

```text
greenhouse-insights/
├── docs/
│   └── design/             # all design docs (product brief, subsystem designs, ...)
├── backend/
│   ├── domain/            # greenhouse, plants, observations, events, state
│   ├── simulation/        # world model: definitions, scenarios, runner, evolution, actioner
│   ├── management/        # decision-making: policy, agent, validation, evaluation (see below)
│   ├── intelligence/      # feature extraction, reconciliation, inference, recommendations
│   ├── evaluation/        # scenario evaluation, consistency checks, recommendation eval
│   ├── application/       # persistence, services, FastAPI routers
│   ├── alembic/           # schema migrations (versions/ has one file per schema change)
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── pyproject.toml     # Poetry: [project] deps, [tool.poetry.group.dev]
│   ├── poetry.lock
│   └── .python-version
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── Dockerfile
│   └── generated/         # OpenAPI-generated typed client (never hand-edited)
├── docker-compose.yml
├── Makefile                # `make help` lists the common dev/test/docker commands
├── .pre-commit-config.yaml
└── DEVELOPMENT_GUIDELINES.md
```

- **Backend:** Python + FastAPI. Pydantic models double as the domain schema and the
  source of the OpenAPI spec. Dependencies are managed with Poetry
  (`poetry install`), not pip/venv directly - `poetry.toml` sets
  `virtualenvs.in-project = true` so `poetry install` still creates
  `backend/.venv`, which is why the pre-commit hooks below can keep doing
  `source .venv/bin/activate` unchanged.
- **Deployment:** `backend/Dockerfile` and `frontend/Dockerfile` are independent
  images (backend: Poetry install + uvicorn; frontend: Vite build served by
  nginx, with an SPA fallback for client-side routes). `docker-compose.yml`
  wires them together for local testing of the deployment artifacts
  specifically - day-to-day development still uses the venv/`npm run dev`
  workflow below, not Docker, for faster iteration.
- **Simulation vs. management vs. execution:** three separate concerns, on purpose. `simulation/`
  owns world state and its evolution - it does not decide anything. `management/` owns
  decision-making (`NoOpPolicy`, `DeterministicPolicy`, the agent) and reads only the
  observable `GreenhouseManagementContext` (`management/context.py`), never simulator-hidden
  truth - it *proposes* `RequestedAction`s and never touches `GreenhouseWorld`. Carrying those
  proposals out is a third, separate concern: `simulation/executor.py`'s `ActionExecutor`
  protocol (`SimulatedOperatorExecutor` today: instantaneous, complete execution), selected
  per simulation via `SimulationDefinition.action_executor`
  (`domain.enums.ActionExecutorType`) the same way `management_policy` is. This mirrors
  `docs/design/greenhouse_agentic_management_design.md` §43/§45: the same management code
  should later run against a real greenhouse by swapping simulated observations for real
  sensors and simulated execution for human approval/robot scheduling/a real robot, with the
  decision logic unchanged - and now the execution side is a real swap point (a future
  `SimulatedRobotExecutor` or a real one is a new `ActionExecutorType` member plus one class),
  not a hardcoded function call. `simulation/runner.py` is the only place that wires all
  three together per day: build context → `management` policy decides → `management.validation`
  checks the result against real state → the resolved `ActionExecutor` executes it.
- **Frontend:** React + TypeScript.
- **API connection:** FastAPI's auto-generated OpenAPI schema is the contract. We generate
  a typed TS client from it (`openapi-typescript` + a thin fetch wrapper, e.g.
  `openapi-fetch`) into `frontend/generated/` on every backend schema change. Never
  hand-write request/response types on the frontend — if the backend changes a field, the
  frontend build breaks immediately instead of drifting silently.
- **Progressive simulation updates:** start with polling against
  `GET /simulations/{id}/status`; move to SSE only if polling proves visually insufficient.
  Per the brief, the transport is an implementation detail — don't over-invest here early.
- **Database:** SQLite via SQLAlchemy Core, one `MetaData` object
  (`backend/application/persistence/schema.py`). Schema changes are managed with Alembic, not
  `create_all` — `create_engine_and_tables` (`backend/application/db.py`) runs `alembic
  upgrade head` on every startup, including in tests. Any change to `schema.py` needs a
  matching migration generated from `backend/` with:
  `alembic revision --autogenerate -m "<description>"`. `test_schema_py_has_no_drift_from_the_migrations`
  (`backend/tests/application/test_migrations.py`) fails the build if a schema change ships
  without one, so this cannot silently drift the way it did once before migrations existed.

---

## 3. Development Workflow

1. Pick one small unit of work (one endpoint, one reconciliation rule, one UI state).
2. Write a failing test that expresses the behavior.
3. Implement the minimum to pass it.
4. Run linters/formatters/type checks locally (or let pre-commit do it).
5. Commit. Commit message format: `<type>: <short imperative summary>`
   (`feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `eval`). `eval` is its own type
   because evaluation harness changes are a distinct, trackable category of work here.
6. Push frequently; keep branches short-lived if branches are used at all at this stage of
   the project (solo/small-team POC — direct small commits to a mainline are fine unless a
   change is large or risky enough to warrant review first).

Avoid:
- Bundling unrelated changes (e.g., a new feature + a formatting sweep) in one commit.
- Committing code with skipped/pending tests without a `# TODO` and a reason.
- "Big bang" commits that add a whole layer (e.g., all of `intelligence/`) at once.

---

## 4. Testing Strategy

Map tests to the domain boundaries, not to implementation files:

| Layer | What's tested | Style |
|---|---|---|
| `domain/` | Invariants of Greenhouse/Plant/Observation/Event/State models | Pure unit tests, no I/O |
| `simulation/` | Scenario engine produces expected observations/events for a given seed | Deterministic (fixed `random_seed`), snapshot-friendly |
| `intelligence/` | Feature extraction, reconciliation, inference rules | Unit tests with hand-built observation/event fixtures + property tests where useful |
| `evaluation/` | Metrics computed correctly against known ground truth | Unit tests on the metric functions themselves |
| `application/` | API contracts, persistence round-trips | Integration tests (real DB or in-memory equivalent, real FastAPI TestClient) |
| `frontend/` | Component behavior, historical navigation logic | Component tests; E2E only for the one end-to-end demo flow (§49 in the brief), not for every screen |

Rules of thumb:
- If a bug is found, add a regression test before fixing it.
- Simulation determinism (fixed seed) is what makes TDD tractable here — never let
  simulation output depend on wall-clock time or unseeded randomness.
- Ground-truth data from the simulator must stay out of `intelligence/` inputs — evaluation
  code is the only place allowed to compare against it.

---

## 5. Evaluation-First Development

Because the simulator is the source of truth, treat evaluation as a spec, not a report card:

- When adding an inference or recommendation rule, write the evaluation check for it
  (precision/recall against ground truth, or exact-match for deterministic facts) in the
  same PR/commit sequence — not as a separate later milestone.
- Prefer deterministic evaluation (exact numeric comparison, set overlap, confidence
  calibration against known outcomes) over subjective/LLM-judged evaluation. The brief is
  explicit that deterministic evaluation should precede LLM-as-judge evaluation (§30, §54).
- Track evaluation results over time (even just as a checked-in JSON/CSV per run) so
  regressions in inference quality are visible across commits, the same way test failures
  are.

---

## 6. Code Quality Tooling

**Backend (Python):**
- [`ruff`](https://docs.astral.sh/ruff/) — linting *and* formatting (replaces
  flake8/isort/black in one fast tool).
- [`mypy`](https://mypy-lang.org/) — static typing, run in strict-ish mode on `domain/` and
  `intelligence/` at minimum.
- [`pytest`](https://docs.pytest.org/) (+ `pytest-cov` for coverage visibility, not as a gate
  at POC stage).

**Frontend (TypeScript/React):**
- `eslint` + `typescript-eslint` — linting.
- `prettier` — formatting.
- `tsc --noEmit` — type checking as its own check, separate from bundling.
- `vitest` + `@testing-library/react` for component tests.

**Both:**
- No commented-out code, no dead branches — delete instead of disabling.
- Type hints/annotations are mandatory in `domain/`, `simulation/`, `intelligence/`,
  `evaluation/`; looser in throwaway scripts is fine.

---

## 7. Pre-commit Hooks

`.pre-commit-config.yaml` runs on every commit, fast checks only (seconds, not minutes):

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
        files: ^backend/

  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest (fast unit tests only)
        entry: bash -c 'cd backend && pytest -m "not slow" -q'
        language: system
        pass_filenames: false

      - id: eslint
        name: eslint
        entry: bash -c 'cd frontend && npx eslint . --max-warnings=0'
        language: system
        pass_filenames: false

      - id: prettier
        name: prettier --check
        entry: bash -c 'cd frontend && npx prettier --check .'
        language: system
        pass_filenames: false

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Slower checks (full test suite including integration/evaluation tests, `mypy --strict`
across the whole backend, E2E frontend tests) belong in CI, not pre-commit — pre-commit
should stay fast enough that nobody is tempted to `--no-verify` past it.

---

## 8. Definition of Done (per commit)

- [ ] Tests written for the behavior added or changed, and passing.
- [ ] `pre-commit run --all-files` passes.
- [ ] If the change touches `intelligence/` or `evaluation/`: an evaluation check exists or
      was updated for it.
- [ ] If the change touches backend Pydantic models exposed via the API: the frontend
      generated client was regenerated.
- [ ] Commit is scoped to one coherent change, with a message that says why, not just what.

---

## 9. What to Avoid

- Introducing an agent/LLM framework before the deterministic backbone (§56 of the brief)
  works end to end.
- Hand-rolled API types on the frontend instead of generating them from the OpenAPI schema.
- Skipping the evaluation harness "until intelligence features are done" — build it
  alongside, since the simulator gives us ground truth for free right now and won't always.
- Large, multi-concern commits that make bisecting or reviewing painful.
- Ground truth leaking into `intelligence/` inputs or API responses.
