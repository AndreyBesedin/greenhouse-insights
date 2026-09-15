# Greenhouse Insights — Technical Reference

This document contains implementation details that are useful when developing, reviewing, or deploying the project but are intentionally kept out of the main README.

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
- `ingestion/` — turning recorded external datasets into the same canonical observations, events and greenhouses (see below). Dataset-specific parsing stays inside `ingestion/wur/...` adapters.
- `domain/` — shared domain models and enums.

Chronology in generic domain records (observations, events, state snapshots, recommendations) is the timestamp alone. The simulation's day counter is a simulation mechanic: `SimulationDefinition.timestamp_for_step` is the one place it becomes an instant, and only simulation-owned objects (`GreenhouseWorld`, management traces/progress) still carry it. This is what lets simulated, recorded and (later) live greenhouses share one state model and one timeline API.

The frontend is React + TypeScript and consumes a generated client from FastAPI's OpenAPI schema.

## Manual simulation workflow

The primary application flow is manual rather than autoplay:

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

The legacy auto-run endpoint remains available for compatibility/testing, but the human-in-the-loop manual flow is the intended product path.

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

## Example scenario

`Agentic Demo Greenhouse` is a small example configuration useful for quickly exercising the agentic workflow.

It contains 6 plants over 15 simulated days and is tuned so ordinary simulator dynamics reach the principal management action types quickly. It is not a scripted sequence of outcomes: the scenario still runs through the normal simulator dynamics with a fixed/configured seed.

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

## Recorded data ingestion

`backend/ingestion/` implements the first phases of `docs/design/wur_real_data_ingestion_replay_plan.md`:

- **Manifests** (`ingestion/manifests/*.json`) describe each source dataset - artifact names, sizes, MD5s, download URLs, licence - and are generated from the 4TU metadata API by `greenhouse-data inventory`, never hand-copied. No raw data is committed.
- **Storage** (`ingestion/storage/`) resolves an artifact as local copy → configured mirrors → upstream download, verifying checksums, resuming downloads, and refusing anything above the calling profile's size cap. Data lives under `GREENHOUSE_DATA_DIR` (default `~/.greenhouse-insights/data`) in `raw/`, `canonical/` and `features/` tiers.
- **Adapters** (`ingestion/wur/agc4_challenge_2024/`) model the 2024 challenge as one greenhouse, `wur_agc4_2024`, with six `Compartment`s (3.01-3.08, team and camera in each description). Each compartment's 5-minute CSV becomes compartment-scoped `Observation`s (23 climate, actuator, setpoint and irrigation channels, local CET/CEST normalised to UTC, `compartment_id` set), and `Harvest.xlsx` becomes sampled-crop observations plus one `HARVEST` event per compartment, stamped at the harvest day the time series records (`dwarf_tomato/harvest_date`). Plant-density changes become a `plant_density_per_m2` observation plus a `SPACING` event per change. The site's `weather.csv` (ten outside channels) and the running daily radiation-sum column of `weather_forecast.csv` become greenhouse-level observations with no compartment. The hourly forecast fields and the wind-direction bit flags are deliberately skipped; `channels.py` records why. The `*_vip` columns become effective-control observations kept next to their setpoints, and coded columns (CO2 dosing on/off) pass through an explicit recode table that refuses unknown codes. Energy and cost columns are increments over the five minutes ending at each row, per m²; reconstruction sums them into local-day totals (`domain/accumulation.py`) instead of keeping the latest value, and an increment stamped exactly at local midnight closes the previous day. Recorded setpoints are observations of control state, not events.
- **2023 pre-trial adapter** (`ingestion/wur/agc4_pretrial_2023/`) models the pre-trial as greenhouse `wur_agc4_2023` with one compartment, `pretrial`, which the dataset does not number. `ClimateTimeseries.xlsx` becomes eight site-weather and eight compartment channels. `CropMeasurements.xlsx` adds the 40 labelled measurement plants (label 47 is split where its plant was replaced) and their weekly manual height, leaf, truss, flower and fruit counts, summed from measured cells only because the sheet's own sums count blanks as zero. `DestructiveHarvest.xlsx` adds 156 destructively sampled plants as `DESTRUCTIVE_SAMPLE` events, not harvests, because sampled biomass is not yield; the sheet's 96 transplant rows are 12 untreated plants copied under eight treatment names, so each collapses to one event naming the rows it was listed as. Its MATLAB datenums are Dutch local wall-clock time: `matlab_datenum_to_utc` converts them and refuses local times that occur twice or never, since the export leaves the repeated DST hour empty. Zone PAR per light treatment waits for spatial regions.
- **Media captures** (`domain/media.py`, table `media_captures`) record images by reference: sensor, compartment, timestamp, modality (RGB, depth, left and right infrared) and an artifact URI `<dataset id>/<artifact name>!<member path>`. Pixels never enter the application database; perception reads the artifact through the storage layer and emits derived observations.
- **Sensors** (`domain/sensor.py`, table `sensors`) hold a sensor's hardware model, device id, per-stream camera intrinsics, and the source's verbal mounting description as text; no numeric pose is stored unless a source states one. `ingestion/wur/common/oak_d.py` reads the WUR Oak-D configs: depth takes the colour intrinsics because the images are aligned, and the 2023 canopy and single-plant cameras are the same physical cameras as 2024 `cam_19` and `camir_27` (identical intrinsics).
- **Canonical tier** (`ingestion/canonical.py`): per-greenhouse JSONL of the domain models plus `provenance.json` with source members, checksums, the compartment selection and output content hashes; deterministic across rebuilds. All six 2024 compartments are about 2.7 million observations and 800 MB of JSONL.
- **Loader** (`ingestion/loader.py`) replaces a greenhouse's records in the application database, optionally only for some compartments, and reconstructs one `GreenhouseState` per local day - the last reading at or before each boundary, values carried forward - so the existing `/timeline` and `/state?at=` endpoints navigate recorded history unchanged. `GreenhouseState.compartments` holds each compartment's readings and harvests; `GreenhouseState.environment` holds only readings scoped to the greenhouse as a whole. Each snapshot also carries a `PlantState` per known plant, including plants inside compartments, with its latest manual readings and `last_measured_at`; health stays `UNKNOWN`, because weekly manual measurements carry no condition evidence.

Profiles: `tiny` (compartment 3.06, tabular only), `dev` (all six compartments, tabular only), `full` (also the ~43 GB image archives). Both datasets have adapters: 2024 for its full tabular data, 2023 for its climate record, weekly crop measurements and destructive samples. Perception, replay-time recommendations and backtesting are later phases of the plan.

## Authentication and authorization

Design: `docs/design/authentication_authorization_plan.md`. The shape in code:

- **Tenancy model** (`application/auth/models.py`): `Organization` is the tenant boundary, `User` is a local identity keyed by the identity provider's stable subject (never by email), `OrganizationMembership` gives a user one role per organization (`VIEWER` < `EDITOR` < `ORGANIZATION_ADMIN`). Platform admin is a flag on the user, not a membership role. Every `Greenhouse` has a mandatory `organization_id`; demo, simulator and WUR-backed greenhouses belong to `SerraPulse Internal` (`org_serrapulse_internal`, created by the migration that made ownership mandatory).
- **Authentication** (`application/auth/identity.py`, `application/auth/oidc.py`, `application/api/auth.py`): an `Authenticator` turns request headers into an `AuthenticatedIdentity`; `UserResolver` maps that to the local `User`, creating it on first login and granting platform admin to subjects listed in `GREENHOUSE_PLATFORM_ADMIN_SUBJECTS` (removing a subject never revokes). `GREENHOUSE_AUTH_MODE` has no default. `dev` trusts an `X-Dev-Subject` header and is for local development and tests only. `oidc` validates RS256 bearer tokens from an OpenID Connect provider (Auth0) against the issuer's JWKS, checking issuer (`GREENHOUSE_OIDC_ISSUER`) and audience (`GREENHOUSE_OIDC_AUDIENCE`); email and name come from configurable claims, falling back to the userinfo endpoint (cached per subject). The authenticator is built once per process and injected via `get_authenticator`.
- **Authorization** (`application/auth/actor.py`, `application/auth/authorizer.py`): routes receive an `ActorContext` from the `get_actor` dependency and hand it to the application services, which authorize every operation against the target greenhouse's organization. `GreenhouseService` is built for an actor; `SimulationService` (one long-lived instance owning locks and tasks) takes the actor per call. Repositories stay authorization-free, so calling them directly is privileged infrastructure code (bootstrap, ingestion, the simulation runner), not a product path.
- **Responses**: no credential is `401`; a resource in an organization the actor cannot read is `404` (identifiers cannot be probed across tenants); a visible resource the actor's role cannot act on is `403`. Creating and deleting greenhouses is platform-admin only for now.
- **Administration** (`application/access_service.py`, routers `organizations.py` and `admin.py`): platform admins create organizations, list users, grant/revoke platform admin (never their own) and move greenhouses between organizations; organization admins list, add (by the email a user signed in with), re-role and remove members. Every privileged mutation appends an `AuditEvent` (`application/auth/audit.py`, table `audit_events`) readable at `GET /admin/audit` (platform) and `GET /organizations/{id}/audit` (per tenant).
- **Frontend**: `src/auth/` holds the session in either mode (`session.ts`: dev subject in `localStorage`, or `oidc.ts` wrapping Auth0's SPA SDK with PKCE and refresh tokens; `VITE_AUTH_MODE` picks one), the `SessionProvider` that loads `GET /me` and remembers the selected organization, the `RequireSession` route guard, and `access.ts` (`canRead`/`canWrite`/`canAdminister`) that the pages use to hide controls. Frontend checks are UX only.

Tests: `tests/application/auth/` (rules, identity resolution, token validation against a locally generated key pair), `test_greenhouse_authorization.py`, `test_simulation_authorization.py` and `test_access_service.py` (tenant isolation and administration through the services alone), and the `_api_` tests (the same over HTTP). `tests/application/support.py` has the fixtures for organizations, members and greenhouses.

## Persistence and migrations

Persistence uses SQLAlchemy Core against either SQLite or PostgreSQL; schema migrations use Alembic.

- Native development defaults to SQLite at `backend/data/greenhouse.db`.
- `docker compose` and the deployment run PostgreSQL 16 (`docker-compose.yml` sets the URL).
- Tests run on SQLite by default; setting `GREENHOUSE_TEST_DATABASE_URL` to a PostgreSQL server URL gives every test its own freshly created database there, which is what CI's `backend-postgres` job does.

Override the application database with `GREENHOUSE_DATABASE_URL` (`sqlite:///...` or `postgresql+psycopg://...`). Repositories build insert-or-update statements through `application/persistence/upsert.py`, the one place that knows about dialects; timestamps are stored as UTC ISO-8601 strings, which compare correctly on both.

The application applies migrations on startup. When changing `application/persistence/schema.py`, create the matching Alembic migration. Migration drift is covered by tests.

A standalone `alembic` CLI invocation does not automatically load `backend/.env`; export `GREENHOUSE_DATABASE_URL` in the shell first when running manual migration commands against a non-default database.

## API and generated frontend client

FastAPI's OpenAPI document is the frontend/backend contract.

Historical navigation is by instant: `GET /greenhouses/{id}/timeline` lists the persisted state checkpoints, and `GET /greenhouses/{id}/state?at=<ISO-8601>` (likewise plant detail, history via `up_to`, and recommendations) returns the state as known at or before that instant. The frontend maps the N-th checkpoint to "Day N" for simulations and to the checkpoint date for recorded data.

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

The stack is three services: `postgres` (PostgreSQL 16, data in the `greenhouse_postgres` volume), `backend` (waits for the database's health check, applies migrations on startup, keeps dataset tiers in the `greenhouse_data` volume via `GREENHOUSE_DATA_DIR=/app/data`) and `frontend`. `POSTGRES_PASSWORD` in the environment (or a top-level `.env`) overrides the throwaway default password. `docker compose down -v` removes both volumes and therefore wipes the database and any imported datasets.

`VITE_API_BASE_URL` is a Vite build-time value. If frontend and backend are deployed to separate origins, rebuild the frontend with the correct API base URL and configure `GREENHOUSE_ALLOWED_ORIGINS` on the backend accordingly.

## Concurrency constraints

The application protects per-simulation read-modify-write operations with in-process async locks. This is appropriate for the current single-process architecture, but it is not a distributed locking strategy. A multi-worker or horizontally scaled deployment would need persistence-backed coordination / transactional concurrency control.

Management progress is also kept in process memory and is therefore currently ephemeral rather than durable/distributed state.

## Development approach

The initial product and architecture were developed iteratively with ChatGPT as a design partner. Most implementation work was then carried out through Claude Code sessions, with the repository owner steering scope, reviewing decisions, testing the result, and iterating on the implementation. Recent commits retain Claude co-author/session metadata for transparency.
