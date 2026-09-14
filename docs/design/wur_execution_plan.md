# WUR Real-Data: Execution Plan

Status: active execution plan, written 2026-09-14. It sequences the work
described in `wur_real_data_ingestion_replay_plan.md` (moved into this folder by
PR #7) into small, independently mergeable steps. Each step is one PR with one
concern. When a step lands, tick it here; when the plan stops being followed,
archive it to `docs/archive/design-history/`.

## Starting point

- **PR #7 (`feat/wur-ingestion-slice`) already implements Phases 0-3.** It was
  verified on 2026-09-14 on a fresh checkout: 331 backend tests, mypy strict,
  70 frontend tests, tsc and eslint all pass; `greenhouse-data prepare --profile
  tiny` + `load --compartment 3.06` build 477,843 observations and 74 daily
  snapshots from the real 4TU archive in under ten seconds. Clean under the
  ruff version pre-commit pins; PR #9 aligns pre-commit and CI on the locked
  ruff so the same holds there.
- **PR #8** is a planning doc for a ThingSpeak live source. It is compatible
  with this plan (same observation model, same source boundary) and does not
  block anything here.
- **Measured dataset facts** (2026-09-14, 4TU API): 2023 pre-trial 12.0 GB
  (4 MB tabular xlsx, 4.5 GB canopy, 7.5 GB single-plant), 2024 challenge
  31.4 GB (6 MB tabular csv, 31.4 GB canopy: 7404 PNG, 6 cameras, 4 captures
  per day). Both CC BY 4.0. 4TU serves HTTP range requests but throttles
  bursts of small ones. A full local mirror lives at
  `~/.greenhouse-insights/data/raw/wur/` on the workstation.
- **No CI exists yet** (`.github/workflows/` is absent). Pre-commit is the only
  gate.

## Decisions taken

1. **Postgres is the application database.** SQLite stays for fast local unit
   tests; CI runs the same suite against Postgres so the two cannot drift.
   Cloud and docker-compose use Postgres. Managed Postgres (RDS) is a later
   URL swap, not a design change.
2. **No Parquet.** Parquet was proposed for an immutable, columnar canonical
   tier readable from S3 without the app DB. PR #7 met that need with
   deterministic JSONL plus sha256 provenance, which at ~130 MB per 2024
   compartment is small enough. Revisit only if backtests over all six
   compartments become I/O-bound.
3. **Canonical artifacts stay files** (local + S3), the DB holds what is loaded
   for replay. This is the separation PR #7 established and it survives the
   Postgres move unchanged. Measured 2026-09-14 after E2c: the full 2024
   greenhouse (4.63M observations) loads into PostgreSQL in 74 s with 115 MB
   of loader memory and takes 1.7 GB on disk, so one host holds it
   comfortably. Revisit when all recorded sources together approach the
   host's volume size.
4. **S3 and a cloud deployment are in scope now**, because the app will be
   public on a domain soon. The first cloud shape is one host running the
   existing docker-compose stack (backend, frontend, Postgres with a volume,
   TLS reverse proxy), plus a private S3 bucket reached through an instance
   role. Terraform describes it.
5. **Compartment becomes a domain entity.** A Greenhouse owns Compartments; a
   compartment owns its environment readings and, when known, its plants.
   The 2024 dataset becomes one greenhouse with six compartments instead of
   six greenhouses. `compartment_id` is optional on generic records so the
   simulator's single-space greenhouses keep working.

## Step list

Each step is one PR. "Done when" is the merge criterion. Tracks can interleave;
dependencies are stated explicitly. Steps marked (S) are safe to do in the same
day as their neighbours.

### Track A - land what exists

- [x] **A1. Merge PR #7.** No code change needed; it is conflict-free against
  main. Done when main has the vertical slice and `make test` passes.
- [x] **A2. Add CI.** PR #9: one GitHub Actions workflow: backend (ruff, mypy,
  pytest on SQLite), frontend (tsc, eslint, prettier, vitest, build), plus
  ruff version alignment between pre-commit and the lock. Done when the
  workflow is green on main and required for PRs.
- [x] **A3. Record Phase 0 facts in the plan doc.** Replace the "not inspected"
  bullets in section 19 with the measured archive structure (camera ids per
  compartment, capture cadence, intrinsics present, no pose), and note the
  4TU throttling behaviour. Docs only.

### Track B - Postgres

- [x] **B1. Dialect-neutral upsert.** Replace the seven
  `sqlalchemy.dialects.sqlite.insert` imports with one helper that picks the
  dialect from the bound engine. Tests unchanged. Done when the suite passes on
  SQLite exactly as before.
- [x] **B2. Postgres in the test matrix.** Add a Postgres service to CI and a
  `GREENHOUSE_TEST_DATABASE_URL` switch in `tests/conftest.py`; run the whole
  suite against it. Nothing broke: the migrations and string timestamps were
  already portable. Done when CI is green on both databases.
- [x] **B3. Postgres in docker-compose.** Add a `postgres` service with a named
  volume, point the backend at it, keep `.env.example` documenting both URLs.
  Done when `make docker-up` boots on Postgres and a simulation runs.
- [x] **B4. psycopg dependency.** Pulled forward into B2. Pool size, timeouts
  and `sslmode` passthrough wait until the deployment needs them.
- [ ] **B5 (later). Native timestamp columns.** Migrate ISO-string timestamp
  columns to `TIMESTAMPTZ` once Postgres is the only production database.
  Not needed for correctness; lexical comparison of UTC ISO strings is
  already correct.

### Track C - cloud baseline (after B3)

- [ ] **C1. Terraform: bucket and role.** Private S3 bucket with versioning,
  an IAM role/instance profile with read/write on it, state backend. Done
  when `terraform apply` creates them and `terraform destroy` removes them.
- [ ] **C2. S3 artifact mirror.** `S3ArtifactMirror` implementing the existing
  `ArtifactMirror` protocol (boto3), configured by `GREENHOUSE_S3_BUCKET`.
  Unit-tested with a stubbed client; one opt-in online test. Done when
  `prepare` on a machine without the raw archive fetches them from S3.
- [ ] **C3. `greenhouse-data sync`.** Push raw and canonical tiers to S3,
  skipping objects whose checksum matches. Run it once from the workstation
  to seed the bucket with the full 43 GB mirror.
- [ ] **C4. Terraform: host.** One small instance, EBS volume for Postgres,
  security group, the instance role from C1, Elastic IP, DNS record for the
  domain. Done when `ssh` works and the role can list the bucket.
- [ ] **C5. Deploy compose stack.** Caddy (automatic TLS) in front of frontend
  and backend, Postgres on the EBS volume, backend reading S3 via the role.
  A `make deploy` target or a GitHub Actions job on push to main. Done when
  the simulator demo runs at the domain over HTTPS.
- [ ] **C6. Ops notes.** Cost estimate, idle behaviour, backup of the Postgres
  volume, destroy procedure. Docs only.

### Track D - Compartment entity (independent of B and C)

- [x] **D1. Domain model.** `Compartment(compartment_id, greenhouse_id, name,
  layout, plants)`; `Greenhouse.compartments: list[Compartment]` (empty for the
  simulator). Pure domain + unit tests. No persistence yet.
- [x] **D2. Persist compartments.** `compartments_json` column and migration;
  repository round trip. Simulator greenhouses store `[]`.
- [x] **D3. `compartment_id` on records.** Nullable column on observations,
  events and recommendations; repositories and canonical JSONL carry it;
  migration backfills `NULL`. Simulator emits `None`.
- [x] **D4. Compartment state.** `CompartmentState(compartment_id,
  environment, plant_states, ...)`; `GreenhouseState.compartments:
  list[CompartmentState]`, with the existing greenhouse-level environment
  kept for records with no compartment. Reconstruction groups by
  `compartment_id`. Snapshot shape changes, so the frontend client is
  regenerated.
- [x] **D5. 2024 adapter emits one greenhouse.** `wur_agc4_2024` with six
  compartments (3.01-3.08, team and camera in the compartment description);
  `prepare --compartment` filters, `load` loads the greenhouse. Canonical
  provenance unchanged in spirit. Done when all six compartments load and
  the byte-identical rebuild check still holds.
- [x] **D6. API and UI.** `GET /greenhouses/{id}/state?at=` returns
  compartments; recorded dashboard gains a compartment selector; list page
  shows compartment count. Frontend tests updated.

### Track E - finish tabular coverage (after D5)

- [x] **E1. Weather and forecast.** `weather.csv` as greenhouse-level (site)
  observations; `weather_forecast.csv` only after confirming whether rows are
  "issued at t" or "valid at t" (temporal honesty depends on it). Measured:
  the hourly forecast fields are valid-time indexed (forecast temperature at t
  matches measured at t to 0.66 degC MAE) with no issue time, so they are not
  ingested; the daily radiation-sum forecast is a running as-of value that
  converges on the day's measured total, so it is. The wind-direction column
  holds undocumented bit flags, not degrees, and is skipped. Ten weather
  channels plus the forecast sum add 253k site observations.
- **E2. Remaining 2024 channels.** Profiled on 2026-09-14: 49 unmapped
  compartment columns, split by what each needs.
  - [x] **E2a. Real final-harvest date.** `dwarf_tomato/harvest_date` is the
    day of year, written once on the harvest day's last row (12:00 local),
    matching each team's final row. Use that instant for the HARVEST event
    (`date_source` names the column) instead of "end of recording", and
    refuse a day number that disagrees with its row.
  - [x] **E2b. Spacing.** `dwarf_tomato/plant_density` changes 56 → 42 → 30 →
    20 plants/m2 at local midnight on team-specific dates (`pot_area` is its
    reciprocal and is skipped). A density observation per row plus a SPACING
    event per change.
  - [x] **E2c. Effective control values.** The ten `*_vip` channels are not
    near-copies: CO2 VIP equals its setpoint only 62% of the time (up to
    1114 ppm apart), irrigation interval 67%. Ingest as effective-setpoint
    types, plus minimum pipe temperature / minimum lee window setpoints, CO2
    dosing state (source 1 on / 2 off, recoded to 1 / 0) and cumulative
    dosing minutes (resets daily around 07:40 local, not midnight).
  - [x] **E2d. Energy and cost increments.** `energy/*` and `economics/*` are
    per-5-minute increments with 1e-10 as a zero placeholder; daily sums are
    plausible (heating 0-1.8 MJ, lighting 0.4-1.1 kWh). Latest-value
    reconstruction is meaningless for them, so this needs an accumulating
    observation rule (daily totals) designed first.
  - [ ] **E2e. Per-sensor extras (after F2).** Three substrate probes per
    compartment for five teams (bulk EC, permittivity, temperature; probes
    differ by about 0.3 degC), and single-team sensors: leaf temperature
    (the `.1` column is an exact duplicate), microclimate, fluorescence,
    biosignals, plant mass (agrifusion reads 18.9 → 3.9, trigger 2503 → 1198,
    both declared kilogram, so the unit is inconsistent). These need the
    Sensor model to keep probe identity.
- [x] **E3. 2023 climate adapter.** `ClimateTimeseries.xlsx` (MATLAB datenum,
  NaN padding rows) to observations for a `wur_agc4_2023` greenhouse with one
  compartment. Measured: datenums are Dutch local wall-clock time with DST (the
  daily radiation centroid moves from 13:36 to 12:11 across 29 October), and
  the export blanks the repeated 02:00-03:00 hour, so ambiguous or nonexistent
  local times are refused rather than guessed. The dataset never numbers the
  compartment, so its id is `pretrial`. Eight site-weather and eight
  compartment channels give 299,280 observations and 65 daily checkpoints.
  Zone PAR (`par1`-`par4`, one per light treatment) waits for spatial regions;
  `ligth_on` is undocumented and fractional, so it is skipped. The
  destructive-harvest Info sheet lists density periods (48, 36, 25, 20
  plants/m2, with 29 September - 9 October unstated) for E4-E5.
- [ ] **E4. 2023 crop measurements.** Weekly per-labelled-plant readings from
  `CropMeasurements.xlsx` become plant-level observations, so the
  plant-centric state and UI get their first real data. Plants are created
  from the label ids and treatment columns.
- [ ] **E5. 2023 destructive harvests** as HARVEST events with per-sample
  parameters.

### Track F - perception seam (after C3 for S3 media, or local mirror)

- [ ] **F1. MediaCapture model + table.** `capture_id, timestamp,
  compartment_id, sensor_id, modality, artifact_uri, provenance`. No pixels in
  the DB.
- [ ] **F2. Sensor + intrinsics.** `Sensor(sensor_id, compartment_id,
  modality, intrinsics_ref)` from the `configs/<cam>.json` files; nominal pose
  "1.5 m above crop, nadir" recorded as a stated assumption, not a measured
  pose.
- [ ] **F3. Register 2024 captures from the zip listing.** Parse filenames
  (`<cam>_YYYY_MM_DD_hh_mm_ss_<modality>.png`, local time) into captures
  without extracting images. Done when 7404 captures exist for six sensors.
- [ ] **F4. Media reader.** Read one member from a local zip or from S3 by
  range request through one interface; decode depth PNG to a numpy array.
- [ ] **F5. First extractor.** Depth statistics (median height proxy, coverage
  fraction) emitting derived observations with extractor version in
  provenance; `features/` tier written deterministically.
- [ ] **F6. 2023 single-plant evaluation.** Height-from-depth against
  `ground_truth_*.json`; report MAE per split; stored under `evaluation/`.
- [ ] **F7. Snapshot profiles with images.** `tiny` gains a fixed set of eight
  captures for one camera, `dev` one camera for one week, built from the
  mirror with a recorded member list and checksums.

### Track G - replay hardening and backtesting (after D6)

- [ ] **G1. Replay "now".** Recorded greenhouses get a settable
  `current_state_timestamp`; every reader path takes `up_to` from it.
- [ ] **G2. Enforce `<= T` at the service layer.** Policy and agent context
  builders can only see the repository view bounded by T; a test asserts a
  later observation is invisible.
- [ ] **G3. Shadow recommendations.** Recorded sources produce recommendations
  marked non-executing; the UI says so; approval is disabled.
- [ ] **G4. Backtest runner.** For a time range and cadence: freeze, predict
  (first target: final red-fruit fresh weight per compartment from
  `Harvest.xlsx`), reveal, score. Deterministic, writes a JSON report.
- [ ] **G5. Reporting split.** Prediction accuracy, action imitation and
  non-evaluable counterfactuals reported separately, per the plan's section
  13.

## Suggested order for the next two weeks

A1 → A2 → B1 → B2 → B3 → C1 → C2 → C3 → D1 → D2 → D3 → C4 → C5 → D4 → D5 → D6

That gets the app public on Postgres with S3-backed data before the compartment
refactor lands, and keeps every PR under a few hundred lines.
