# WUR Real-Data Ingestion & Replay Plan

Status: active plan, partially implemented. See "Implementation status" at the end for what exists and what is still open; `docs/technical_reference.md` describes the implemented parts.

## Why this page exists

Greenhouse Insights currently proves its architecture against a controllable simulated greenhouse. The next major step is to run the same observable-state and intelligence pipeline against **recorded real greenhouse data** without replacing the simulator.

The WUR Autonomous Greenhouse Challenge datasets are a good first target because they combine environmental time series, crop measurements, RGB-D imagery and, in the 2024 challenge, recorded control trajectories and outcomes.

The goal is not to reproduce the WUR competition or build a winning greenhouse controller. The goal is to answer a more basic product and architecture question:

> Can Greenhouse Insights ingest heterogeneous real greenhouse observations, reconstruct a coherent longitudinal state, derive useful features from sensing, and produce predictions or operational intelligence using only information that would have been available at that point in time?

The simulator remains essential for counterfactuals and closed-loop policy evaluation. Recorded data adds a second, complementary source of truth: what actually happened in a real greenhouse.

---

## 1. Datasets in scope

Both WUR releases should be supported through the same canonical ingestion model.

### 2023 pre-trial dataset

WUR / 4TU DOI: `10.4121/e1ee9de9-6ce9-4502-a37c-34b5b1372bed`

Known contents:

- `Single_Plant_Camera.zip`: 479 individually RGB-D-imaged dwarf tomato plants with traits including height, fresh weight, leaf area and number of red fruits;
- `Canopy_cam.zip`: longitudinal RGB-D canopy imagery captured four times per day over roughly two months;
- `Timeseries.zip`: manual plant measurements plus 5-minute greenhouse climate and weather data.

Primary uses:

- validate the common ingestion format;
- establish the first perception pipeline on labelled individual plants;
- evaluate simple image-derived measurements against supplied traits;
- exercise longitudinal canopy replay on a real greenhouse history.

### 2024 challenge dataset

WUR / 4TU DOI: `10.4121/fa102772-32db-4b30-bace-12f2016722ce`

Known contents:

- `Timeseries.zip`: 5-minute greenhouse climate, control state and weather data plus plant / yield measurements;
- `Canopy_camera.zip`: longitudinal RGB-D canopy imagery for each of six greenhouse compartments, captured four times per day during the crop cycle.

Primary uses:

- full recorded-data replay;
- multi-compartment longitudinal analysis;
- temporal forecasting and backtesting;
- comparison with recorded control trajectories and later outcomes;
- future spatial and perception research.

### Exact size is deliberately not assumed

The first implementation task is to query 4TU metadata and create a machine-readable inventory of all files, exact byte sizes, checksums, versions, licence metadata and download URLs.

No architecture decision should depend on guessed dataset size.

---

## 2. Design principles

1. **No WUR raw data in Git.** The repository contains code, schemas, manifests and very small deterministic test fixtures only.
2. **Laptop-friendly development is a first-class requirement.** A developer must be able to work from a low-storage / low-compute laptop using a small snapshot or remote data.
3. **Full-data processing is optional locally.** A larger workstation may hold the whole dataset; cloud compute may process it directly from object storage.
4. **Raw data is immutable.** Imported WUR archives are mirrored unchanged. Normalization and perception outputs are separate derived artifacts.
5. **2023 and 2024 converge into one canonical domain representation.** Dataset-specific parsing stays inside ingestion adapters.
6. **Simulation, recorded data and live sensing differ at the source / execution boundary, not in the core observable-state model.**
7. **Nothing outside `simulation/` should depend on `simulated_day`.** Generic domain data uses timestamps.
8. **Spatial identity refers to the physical greenhouse, not to a camera.** Cameras are sensors with poses and fields of view inside a greenhouse coordinate system.
9. **Perception is a real subsystem boundary from the start, but V0 stays simple.** We design for tracking / 3D reconstruction later without trying to implement it now.
10. **Replay must be temporally honest.** At replay time `T`, intelligence may only access records with timestamps at or before `T`.
11. **Recorded history is not a counterfactual simulator.** A recommended alternative action cannot rewrite the WUR future.

---

## 3. Target architecture

```text
                     PHYSICAL / SYNTHETIC INPUTS

       Simulator              Recorded dataset              Live greenhouse
           │                         │                            │
           │                    ingestion                   ingestion
           │                         │                            │
           └────────────── observation sources ──────────────────┘
                                      │
                                      ▼
                         canonical observations / events
                           media / provenance / actions
                                      │
                         perception where applicable
                                      │
                                      ▼
                             state reconstruction
                                      │
                           longitudinal intelligence
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                forecasts         analytics       recommendations
                                                        │
                                                        ▼
                                                 requested actions
                                                        │
                         ┌───────────────────────────────┼──────────────┐
                         │                               │              │
                    simulation                     recorded data     live
                         │                               │              │
                      execute                          shadow     human / robot /
                         │                               │       external controller
                    world changes                 history cannot
                         │                          be rewritten
                   new observations
```

The intelligence layer should not need to know whether an observation originated from simulation, WUR replay or a future live greenhouse.

---

## 4. Data storage and access

### 4.1 Storage tiers

Use three logical layers:

```text
raw/
  exact source artifacts, immutable

canonical/
  normalized records produced deterministically by ingestion

features/
  derived outputs from perception / feature extraction
```

Example S3 layout:

```text
s3://<bucket>/
  raw/
    wur/
      agc4-pretrial-2023/v1/
      agc4-challenge-2024/v1/
  canonical/
    wur/
      agc4-pretrial-2023/v1/
      agc4-challenge-2024/v1/
  features/
    wur/
      agc4-pretrial-2023/<extractor-version>/
      agc4-challenge-2024/<extractor-version>/
```

Local equivalent:

```text
${GREENHOUSE_DATA_DIR:-~/.greenhouse-insights/data}/
  raw/
  canonical/
  features/
```

### 4.2 Resolution order

Dataset access should resolve artifacts in this order:

```text
requested artifact
      ↓
local copy available?
  ├─ yes → use local
  └─ no
       ↓
S3 mirror available / configured?
  ├─ yes → fetch or stream from S3
  └─ no
       ↓
4TU upstream available?
  ├─ yes → fetch from source
  └─ no → clear error with remediation
```

The exact precedence should remain configurable so cloud jobs can prefer S3 and local development can prefer disk.

### 4.3 Dataset manifests

Git should contain manifests, not the data itself.

A manifest should record at minimum:

```yaml
id: wur_agc4_2024
version: 1
source:
  provider: 4tu
  dataset_uuid: fa102772-32db-4b30-bace-12f2016722ce
  doi: 10.4121/fa102772-32db-4b30-bace-12f2016722ce
licence: <filled from source metadata>
artifacts:
  - name: <source file>
    size_bytes: <from metadata>
    checksum: <from metadata>
    download_url: <from metadata>
```

The inventory step should generate / verify this data rather than relying on manually copied file metadata.

### 4.4 Reproducible snapshots

A snapshot is a deterministic subset of a source dataset for local development. It is not a separately curated dataset and must remain traceable to source artifact + selection rule.

Support at least three profiles:

- `tiny`: metadata + time series + a very small number of image captures; designed for constrained laptops;
- `dev`: full time series plus a representative limited image window / compartment and a subset of labelled 2023 plant samples;
- `full`: all source artifacts.

Exact size targets should be chosen after Phase 0 discovers the real archive sizes. As a starting constraint, `tiny` should aim to stay comfortably below 1 GB if the source encoding permits it; `dev` should stay small enough for ordinary laptop work rather than becoming a hidden full download.

Snapshot rules should be deterministic, e.g.:

- fixed compartment(s);
- fixed date range(s);
- fixed image timestamps;
- fixed labelled plant sample IDs / deterministic seed;
- always include metadata required to interpret selected records.

A snapshot manifest should record every included source file / member and checksum.

---

## 5. Cloud-capable execution without making cloud mandatory

The project must support two equally valid workflows:

### Lightweight laptop mode

- run backend + frontend locally;
- use `tiny` or `dev` snapshot;
- no GPU requirement;
- perception can use precomputed features from S3 when desired;
- do not silently pull the full WUR dataset.

### Full local workstation mode

- same application and commands;
- `GREENHOUSE_DATA_DIR` points to large local storage;
- full WUR artifacts may be downloaded once;
- GPU-heavy perception may run locally;
- outputs remain compatible with cloud-produced features.

### AWS mode

Keep the first cloud topology deliberately simple:

```text
                         S3
              raw / canonical / features
                         ▲
                         │
              ┌──────────┴──────────┐
              │                     │
        application host      optional compute job
        backend + frontend       CPU / GPU
              │                     │
              └──────────┬──────────┘
                         │
                    S3 artifacts
```

Initial deployment can reuse the current Docker-based application on a single persistent host rather than prematurely introducing a distributed platform.

Recommended first AWS shape:

- S3 for WUR raw data, canonical data and derived feature artifacts;
- one small persistent compute host for the existing frontend/backend stack;
- persistent block storage for the current SQLite application DB while the project is still single-user / experimental;
- optional on-demand larger CPU/GPU compute for perception jobs that reads from S3 and writes results back to S3;
- IAM roles rather than long-lived AWS credentials in the repository;
- private bucket by default;
- infrastructure described reproducibly (Terraform is preferred if / when this baseline is implemented).

Moving the application database to managed PostgreSQL is a later production concern, not a prerequisite for WUR ingestion.

Large image payloads should not need to pass through the application DB. Store artifact references / metadata in the domain or persistence layer and keep binary data in local object storage / S3.

---

## 6. Phase -1 — cloud-capable runtime baseline

**Purpose:** make heavy-data work possible without making every development machine heavy.

This is a parallel enabler rather than a strict chronological prerequisite. Provisioning it should be triggered by the Phase 0 size / workflow decision rather than done blindly before understanding the dataset.

Deliverables:

- deploy the existing frontend + backend from Docker on AWS with no WUR-specific behavior;
- preserve current simulation functionality;
- attach durable application storage;
- create a private S3 data bucket and environment-based storage configuration;
- establish IAM-based access from the app / processing jobs;
- document deploy / destroy commands and expected costs / idle behavior;
- prove that a small example artifact can be read from and written to S3;
- keep local Docker / native development unchanged.

Definition of done:

> The same Git revision can run locally or in AWS; cloud availability is an option, not a dependency.

---

## 7. Spatial model

A camera region is not a domain object. The greenhouse exists independently of its sensors.

Target concepts:

```text
Site
 └─ Greenhouse
     └─ Compartment
         ├─ physical coordinate frame
         ├─ spatial regions / rows / beds / zones
         ├─ plants (when identifiable)
         └─ sensors
```

A strict tree is useful for containment but should not be the only spatial representation: physical observation regions may overlap.

### Coordinate frame

Introduce a greenhouse / compartment-local coordinate frame capable of representing positions in physical space.

Conceptually:

```text
CoordinateFrame
  id
  parent_frame?
  origin / transform
  units

SpatialRegion
  id
  greenhouse_id / compartment_id
  geometry or bounds in a coordinate frame
  quality / precision metadata where useful
```

### Sensors

A sensor belongs to the sensing layer, not the physical world hierarchy.

```text
Sensor
  id
  type / modality
  calibration_ref?

SensorPose
  sensor_id
  timestamp
  coordinate_frame
  pose / transform
  quality?
```

For a fixed WUR camera, pose may be constant. A future rail robot / mobile camera produces time-varying poses without changing the greenhouse's physical representation.

The first WUR implementation must use only calibration / geometry actually supported by the source data. Unknown spatial information stays unknown rather than being fabricated.

---

## 8. Canonical observations, captures and provenance

The generic observation model should support data from simulation, WUR, real sensors and future perception outputs.

Conceptually:

```text
Observation
  timestamp
  greenhouse_id
  property / type
  value
  unit
  spatial_ref?
  entity_ref?
  source
  sensor_ref?
  confidence?
  quality?
  provenance
```

Plant identity is optional. A valid observation can describe a compartment, physical zone, row, plant, truss or fruit depending on what is actually known.

### Raw media remains first-class

Do not reduce an RGB-D capture to features and lose its identity.

Conceptually:

```text
MediaCapture
  capture_id
  timestamp
  sensor_id
  modality: RGB | DEPTH | IR | ...
  artifact_uri
  spatial_ref?
  sensor_pose_ref?
  calibration_ref?
  source
```

Derived perception should remain traceable:

```text
MediaCapture
    ↓ processed by
PerceptionExtractor(version/config)
    ↓
Derived Observation(s)
```

This preserves reproducibility when the CV model changes later.

---

## 9. Observation-source cleanup

The current project already has `RecordSource`, but generic domain records still contain simulation-specific fields such as `simulated_day`.

Target source categories should distinguish at least:

- simulation;
- recorded dataset / imported historical source;
- live sensors;
- external API / manual sources where relevant.

Avoid introducing a large abstract framework just to encode these names. The useful contract is that every source eventually produces the same canonical observations / events / captures.

### Timestamp rule

Outside `simulation/`, domain chronology is timestamp-based.

`simulated_day` may remain an internal simulation mechanic on hidden world / simulation-run objects. When the simulator emits an `Observation`, `Event`, state snapshot or recommendation into the generic system, it emits a timestamp derived from the configured simulation clock.

The refactor must remove `simulated_day` from generic domain and persistence paths, including generic observation / event / state / recommendation records.

Where a crop-relative day is later useful, model it explicitly as derived metadata (`crop_day`, `days_since_planting`, etc.) rather than preserving simulation terminology.

---

## 10. Ingestion and perception boundaries

Create these boundaries early even when implementations are small.

Suggested direction:

```text
backend/
  ingestion/
    storage/
    wur/
      common/
      agc4_pretrial_2023/
      agc4_challenge_2024/

  perception/
    extractors/
    tracking/       # placeholder / future
    geometry/       # placeholder / future
```

This layout is directional rather than a requirement to add empty packages for every future subsystem. Add packages when the first implementation needs them, but do not put WUR-specific parsing into the core domain or perception logic.

### Ingestion responsibilities

- discover / fetch artifacts;
- verify checksum and version;
- unpack / read source formats;
- map WUR identifiers to internal source identities;
- normalize time, units and metadata;
- create canonical captures / observations / events;
- persist canonical records or produce deterministic canonical artifacts;
- never perform crop-management reasoning.

### Perception responsibilities

V0 should be deliberately modest:

- load RGB / depth media through the generic capture model;
- extract one or more simple, testable features;
- emit derived observations with extractor version + provenance;
- validate against WUR labels where labels exist.

Possible early features:

- canopy height from depth;
- canopy coverage / area proxy;
- coarse colour / red-fruit signal;
- basic depth statistics.

Explicitly postponed but architecturally anticipated:

- learned fruit / leaf / truss detection;
- instance segmentation;
- persistent plant identity;
- fruit / truss identity;
- multi-view association;
- camera calibration refinement;
- mobile-camera pose estimation;
- 3D greenhouse reconstruction;
- SLAM-like geometry;
- temporal tracking and occlusion reasoning.

---

## 11. Replay semantics

A recorded greenhouse is a greenhouse whose observation history already exists.

Replay is how the application traverses that history; it should not become a fake simulator.

At replay time `T`:

```text
all canonical records with timestamp <= T
                    ↓
             state reconstruction
                    ↓
          features / intelligence
                    ↓
        forecasts / recommendations
```

The system must not expose future records to policy, agent or state reconstruction.

Historical navigation should reuse the existing product idea of time travel, but the source is recorded observations rather than generated simulator steps.

---

## 12. Action behavior: simulation vs recorded replay

The **decision generation path should remain shared** as far as possible:

```text
observable history <= T
        ↓
state / intelligence / policy
        ↓
requested action / recommendation
```

After that point the environments diverge.

### Simulation

```text
requested action
      ↓
validation + executor
      ↓
hidden world changes
      ↓
future observations change
```

This allows counterfactual and closed-loop policy evaluation.

### Recorded WUR replay

```text
requested action
      ↓
shadow recommendation
      ↓
recorded future remains unchanged
```

The application can display what it would have recommended, but must not pretend that the historical outcome proves whether an alternative action would have been better or worse.

Recorded control actions may be compared with generated actions as an **imitation / disagreement diagnostic**, not treated as optimal ground truth.

---

## 13. Temporal evaluation

Temporal backtesting is the main real-data evaluation pattern.

For each evaluation timestamp `T`:

1. expose only data with `timestamp <= T`;
2. reconstruct state;
3. generate predictions / analytics / recommendations;
4. persist the prediction with model / feature / source versions;
5. reveal later recorded observations to the evaluator only;
6. score claims that are actually observable in the future.

### Strongly evaluable from recorded data

Examples:

- image-derived measurements vs labelled / manual measurements;
- state reconstruction against later / independent measurements;
- future ripe fruit / harvest estimates;
- crop-development forecasts;
- anomaly / event inference when later evidence exists;
- calibration and uncertainty of predictions.

### Diagnostic but not ground truth

Examples:

- whether a recommended action matches a recorded team / controller action;
- timing difference between generated and historical interventions.

These are useful disagreements to inspect, not proof of correctness.

### Not causally evaluable from one recorded trajectory

Examples:

- whether a different irrigation action would have improved yield;
- whether an alternative climate strategy would have produced more profit;
- whether a generated management policy dominates the historical policy.

Those questions require simulation, a causal model or a real controlled experiment.

---

## 14. Implementation phases

### Phase 0 — source inventory, size discovery and decision gate

Do this before downloading the full archives.

Deliverables:

- query the 4TU API for both dataset UUIDs;
- record source version, licence, file list, exact compressed sizes, checksums and download URLs;
- estimate extracted sizes where practical after inspecting archive metadata;
- classify source files by metadata / time series / labelled images / longitudinal RGB-D;
- commit generated / reviewed dataset manifests;
- test resumable download of one small artifact or byte-limited sample where possible;
- verify whether archives support selective access or require full archive download;
- estimate S3 monthly storage and likely transfer / processing footprint before provisioning heavy compute.

Decision gate:

```text
Can the useful full dataset fit comfortably on ordinary dev machines?
    ├─ yes → full local support remains easy
    └─ no  → snapshot-first laptop workflow + S3 full mirror becomes primary
```

Regardless of the answer, snapshots remain useful for deterministic tests and lightweight development.

### Phase -1 — cloud-capable runtime baseline (conditional / parallel)

If Phase 0 confirms that full data is inconvenient locally, implement the AWS baseline described above.

Deliverables:

- current app deploys unchanged in cloud;
- simulations still work;
- private S3 artifact store available;
- small S3 read/write integration proven;
- optional processing job path established;
- no requirement for developers to run AWS locally.

### Phase 1 — remove simulation chronology from generic domain

Deliverables:

- `simulated_day` retained only in simulation-owned mechanics / hidden world objects;
- observations, events, state and recommendations use timestamps;
- persistence and APIs migrate accordingly;
- historical UI behavior remains correct;
- simulation emits deterministic timestamps from its internal clock;
- regression tests cover current simulator flows.

### Phase 2 — storage resolver + canonical source contracts

Deliverables:

- local / S3 / upstream artifact resolution;
- checksum verification;
- source manifests;
- dataset / capture provenance;
- initial physical coordinate / spatial region / sensor concepts required by WUR;
- no WUR-specific fields in shared domain models.

### Phase 3 — WUR 2023 and 2024 ingestion

Start with tabular / metadata paths before image processing.

Deliverables:

- both datasets import through separate WUR adapters;
- units and timestamps normalized;
- greenhouse / compartment mapping explicit;
- WUR measurements become canonical observations / events;
- 2024 control history retained as recorded actions / control observations where semantically appropriate;
- one `tiny` and one `dev` snapshot definition generated reproducibly;
- canonical output can be inspected without loading raw image archives.

Initial vertical slice:

> One real WUR compartment / greenhouse window → canonical observations → current state reconstruction → historical UI.

### Phase 4 — minimal perception seam

Deliverables:

- media capture model and artifact references;
- RGB-D loading through generic interfaces;
- at least one simple derived feature emitted as a canonical observation;
- extractor version recorded in provenance;
- at least one 2023 labelled task evaluated automatically;
- full CV roadmap remains out of scope.

### Phase 5 — recorded-data replay

Deliverables:

- select a recorded greenhouse / compartment;
- move through real timestamps / available observation boundaries;
- strict `<= T` access enforced at service / repository level;
- reconstructed state rendered through existing UI concepts;
- future information never leaks into state, policy or agent calls;
- recommendations are visibly shadow / non-executing for recorded sources.

### Phase 6 — temporal backtesting

Deliverables:

- deterministic backtest runner over a chosen time range;
- forecast / measurement evaluation against later observations;
- separate reporting for prediction accuracy, action imitation and non-evaluable counterfactual recommendations;
- no misleading "policy quality" metric derived from historical action matching alone.

### Phase 7 — expand real-data coverage

Only after the vertical slice is reliable:

- full 2023 + 2024 seasons;
- all six 2024 compartments;
- richer perception;
- zone-level longitudinal features;
- plant / truss / fruit identity experiments where the data support them;
- larger cloud GPU jobs;
- compare simulator-generated and recorded distributions;
- prepare for first live greenhouse source.

---

## 15. Suggested developer commands

Exact command names can change during implementation, but the workflow should become this simple:

```bash
# metadata only; no heavy download
poetry run greenhouse-data inventory wur agc4-2024

# tiny constrained-laptop snapshot
poetry run greenhouse-data prepare wur agc4-2024 --profile tiny

# representative development snapshot
poetry run greenhouse-data prepare wur agc4-2024 --profile dev

# full source data on workstation / cloud
poetry run greenhouse-data prepare wur agc4-2024 --profile full

# optional S3 mirror / synchronization
poetry run greenhouse-data sync wur agc4-2024 --to s3

# recorded replay
poetry run greenhouse-data replay wur agc4-2024 --at <timestamp>
```

A command requesting `tiny` or `dev` must never silently upgrade itself into a full image download.

---

## 16. Testing strategy

### Unit

- source manifest parsing;
- unit / timestamp normalization;
- storage resolver precedence;
- snapshot selection determinism;
- spatial transforms where implemented;
- WUR parser fixtures;
- simple perception extractors.

### Integration

- one very small checked-in fixture representing source format structure;
- download metadata from 4TU without downloading large archives;
- import a local snapshot;
- S3 resolver against a test / development prefix;
- canonical persistence round trip;
- replay access cannot read future timestamps.

### Evaluation

- 2023 label-based feature evaluation;
- temporal backtest on recorded future data;
- keep simulation-ground-truth evaluation unchanged and separate.

Large public datasets should not be required to run ordinary CI.

---

## 17. Open questions to resolve during Phase 0 / first ingestion

- Exact compressed and extracted sizes of both WUR releases.
- Exact licence / redistribution constraints and whether maintaining a private S3 mirror requires any attribution / handling rules beyond ordinary use.
- Archive structure and whether image members can be selectively downloaded or only extracted after pulling the whole archive.
- Which camera calibration / pose / spatial metadata is actually present.
- Whether the 2024 source contains explicit mappings for plant / pot identity across spacing changes.
- How best to represent 5-minute control-state values: observations, recorded actions, or both depending on semantic type.
- Minimum useful WUR snapshot that stays genuinely small.
- Whether canonical records belong primarily in the application DB or as columnar / artifact datasets with the DB indexing metadata; choose based on measured volume rather than assumption.
- Whether replay timestamps should advance event-by-event or use product-friendly time checkpoints while preserving exact underlying timestamps.

---

## 18. Definition of success for the first real-data milestone

The first milestone is successful when all of the following are true:

1. A low-storage laptop can clone the repository, prepare a small WUR snapshot and run the application without downloading the full image dataset.
2. The same code can operate against a full WUR mirror on a large workstation or AWS/S3.
3. One WUR greenhouse / compartment time window appears in Greenhouse Insights as a real recorded history rather than a simulation.
4. Generic domain records no longer expose simulation-specific chronology.
5. At least one real RGB-D capture produces a versioned, traceable derived observation through the perception boundary.
6. The system can freeze at time `T`, reconstruct state with no future leakage, make at least one measurable prediction, then evaluate it against later recorded data.
7. The simulator remains fully functional and remains the place where alternative actions can actually change the future.

That would move the project from "real software around a synthetic agricultural world" to a system that can ingest and reason over genuine greenhouse sensing while preserving the simulator for the questions recorded data cannot answer.

---

## 19. Implementation status (2026-09-11)

Implemented, on the branch merged as PR #7:

- **Phase 0 - inventory: done.** `greenhouse-data inventory` generates and verifies the manifests in `backend/ingestion/manifests/` from the 4TU API. Findings: both releases are CC BY 4.0, version 1; the tabular archives total about 10 MB (2024: 6 MB timeseries; 2023: 4 MB), the image archives about 43 GB (2024 canopy 31.4 GB; 2023 canopy 4.5 GB, single-plant 7.5 GB). 4TU serves HTTP range requests, so archive members can in principle be read selectively. Decision gate: full data does not fit comfortably on a laptop, but everything the tabular phases need does, so the snapshot-first workflow is primary and no cloud mirror is required yet.
- **Phase -1 - cloud baseline: deliberately not started.** Nothing before perception needs S3; the resolver's mirror seam (`ingestion/storage/resolver.py`) is where an S3 mirror plugs in.
- **Phase 1 - simulation chronology removed from generic records: done.** Observations, events, state snapshots, recommendations and the management context are timestamp-only; the simulation clock is `SimulationDefinition.timestamp_for_step`; API and UI navigate by instant (`/timeline`, `?at=`); migration `5d1e7a9c2b41`.
- **Phase 2 - storage resolver and source contracts: done for the tabular case.** `GREENHOUSE_DATA_DIR` layout, local → mirror → upstream resolution, checksum verification, resumable downloads, per-profile download caps, canonical provenance. Spatial / sensor / capture concepts (sections 7-8) are not built: the tabular data needs only compartment identity, modelled as `GreenhouseLayout(kind="compartment")`.
- **Phase 3 - WUR ingestion: 2024 done, 2023 not started.** The 2024 adapter maps 23 channels to observations and the harvest workbook to sampled-crop observations plus a compartment-level HARVEST event; canonical output is deterministic; the loader reconstructs one state per local day; `tiny`/`dev`/`full` profiles exist. Compartment 3.06 renders in the UI as recorded history. Not ingested yet: the 2024 weather / weather-forecast files, `*_vip` setpoint duplicates, CO2 dosage counters, economics and energy accumulators, the 2023 workbooks (climate time series, weekly crop measurements, destructive harvests).

Resolved open questions from section 17:

- 5-minute control state is represented as observations (setpoints are observed controller state), not events; discrete manual harvests are events.
- Canonical records live as JSONL artifacts under `canonical/`; the application DB holds what is loaded for replay (one compartment at 23 channels is about 480k rows, loads in seconds).
- Replay checkpoints are product-friendly (one per local day) while snapshot timestamps stay the exact instant of the last reading at or before the boundary.
- Licence: CC BY 4.0 - attribution to WUR / 4TU is carried in each greenhouse description and manifest; no other handling rule found.

Still open / not started:

- **Phase 4 - perception seam:** media capture model, RGB-D loading, a first derived feature, the 2023 label-based evaluation.
- **Phase 5 - replay hardening:** choosing a replay "now" other than the end of the recording, strict `<= T` enforcement at the service layer for policy and agent calls, shadow (non-executing) recommendations for recorded sources. Today a recorded greenhouse has no policy attached and the UI states that its history cannot change.
- **Phase 6 - temporal backtesting** and **Phase 7 - coverage expansion** (all six compartments in one view, the 2023 season, richer perception).
- Archive structure of the image zips, camera calibration/pose metadata, and 2024 plant/pot identity across spacing changes have not been inspected.
