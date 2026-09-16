# ThingSpeak Live Ingestion Plan

Status: planning document. This describes a small live-data integration experiment; it does not imply that ThingSpeak is a production dependency or preferred greenhouse platform.

## Why this page exists

Greenhouse Insights currently supports simulation and is planning replay of recorded WUR data. The next complementary step is to prove that the same observable-state pipeline can consume a **real, changing external sensor stream**.

ThingSpeak is a useful first target because public channels expose timestamped telemetry through simple HTTP APIs. The goal is not to build product-specific logic around hobbyist greenhouses. The goal is to exercise the live-ingestion boundary with real-world timestamps, missing data, irregular updates, external identifiers and continuously arriving observations.

The experiment should answer:

> Can Greenhouse Insights ingest a live third-party greenhouse feed, normalize it into canonical observations with provenance, keep it up to date safely, and display / reason over that data without coupling the core domain to ThingSpeak?

---

## 1. Scope

### In scope

- one public ThingSpeak greenhouse channel as the initial fixture;
- read-only polling of public channel feeds;
- mapping selected fields to canonical environmental observations;
- preservation of source timestamps and channel/field provenance;
- idempotent incremental ingestion;
- basic handling of stale, missing and malformed values;
- creation of a live greenhouse / source configuration separate from simulation;
- backend tests using recorded HTTP fixtures, not the public API;
- a small UI indication of source freshness and last observation time.

### Out of scope

- control / actuation through ThingSpeak;
- credentials or private channels in V0;
- generic IoT-platform abstraction covering every provider;
- high-frequency streaming infrastructure;
- plant-level perception;
- treating the selected public channel as agronomic ground truth;
- product decisions based on hobbyist greenhouse data.

---

## 2. Design principles

1. **ThingSpeak is an adapter, not a domain.** No core model should depend on ThingSpeak channel IDs, field numbers or response shapes.
2. **Live observations use timestamps, never `simulated_day`.**
3. **Source identity is explicit.** Every imported record is traceable to provider, channel and upstream entry.
4. **Ingestion is idempotent.** Re-polling overlapping windows must not duplicate observations.
5. **External data is untrusted input.** Parse and validate units/types/ranges before creating canonical observations.
6. **Staleness is data.** A feed that stops updating must remain distinguishable from a stable greenhouse value.
7. **No network dependency in tests.** Unit/integration tests use deterministic fixtures.
8. **Keep V0 small.** This is a plumbing test before professional greenhouse access, not a new platform subsystem.

---

## 3. Target flow

```text
ThingSpeak public channel
        │
        │ HTTPS polling
        ▼
ThingSpeak adapter
        │
        ├─ channel metadata
        ├─ field mapping
        ├─ timestamp normalization
        └─ value validation
        │
        ▼
canonical Observation records
        │
        ├─ greenhouse / spatial reference
        ├─ observation type + unit
        ├─ timestamp
        ├─ source = external API / live sensor
        └─ upstream provenance
        │
        ▼
state reconstruction / longitudinal history
        │
        ▼
existing API + UI + future intelligence
```

The intelligence layer should not know whether an observation was produced by the simulator, WUR replay, ThingSpeak or a future commercial sensor gateway.

---

## 4. Configuration model

Prefer explicit configuration over hard-coded field assumptions.

Conceptually:

```yaml
source:
  id: thingspeak_demo_greenhouse
  provider: thingspeak
  channel_id: 12345
  poll_interval_seconds: 60
  greenhouse_id: gh_thingspeak_demo
  fields:
    field1:
      observation_type: AIR_TEMPERATURE_C
      unit: C
    field2:
      observation_type: RELATIVE_HUMIDITY_PCT
      unit: percent
    field3:
      observation_type: SOIL_MOISTURE_PCT
      unit: percent
```

Do not infer semantic meaning from a field number. The mapping is configuration.

If a public source lacks trustworthy unit metadata, units must be specified explicitly or the field should remain unsupported.

---

## 5. Provenance and idempotency

For each upstream entry preserve enough identity to answer where it came from and avoid duplication.

Suggested provenance fields / metadata:

```text
provider = thingspeak
channel_id
entry_id
field_id
source_timestamp
fetched_at
source_url / source reference where appropriate
```

A deterministic upstream key can be built from `(provider, channel_id, entry_id, field_id)`.

Re-fetching an already-ingested entry should be a no-op unless the project later deliberately supports upstream corrections.

---

## 6. Polling strategy

V0 does not need websockets, queues or distributed workers.

Use a small polling service:

1. read the last successfully ingested upstream entry / timestamp;
2. request a bounded overlap window from ThingSpeak;
3. validate and normalize returned records;
4. upsert / ignore duplicates transactionally;
5. record ingestion health / last success;
6. sleep until the next poll.

The overlap is intentional so transient failures around boundaries do not lose data; idempotency makes this safe.

Polling should support a one-shot command for development and tests in addition to any long-running mode.

Possible commands:

```text
make backend-ingest-thingspeak-once
make backend-ingest-thingspeak-live
```

Exact CLI naming can follow existing project conventions when implemented.

---

## 7. Data quality and freshness

The first live integration should introduce minimal but explicit quality concepts.

Track at least:

- last source timestamp;
- last successful fetch time;
- parse / validation failures;
- expected poll cadence;
- stale threshold;
- missing fields;
- rejected impossible / non-numeric values.

A stale feed must not silently appear as a current state.

For UI/API purposes, expose something like:

```text
source_status: LIVE | STALE | ERROR | UNKNOWN
latest_observation_at
last_ingestion_success_at
```

Do not overbuild a full device-management subsystem yet; this is enough to expose the first real failure modes.

---

## 8. Backend implementation direction

Suggested boundary, adjusted to the WUR ingestion plan rather than creating a parallel architecture:

```text
backend/
  ingestion/
    thingspeak/
      client.py
      config.py
      mapper.py
      service.py
```

Responsibilities:

### Client
- HTTP calls and ThingSpeak response decoding;
- bounded timeout / retry behavior;
- no domain logic.

### Config
- source/channel configuration;
- explicit field-to-observation mappings;
- polling settings.

### Mapper
- convert provider records to canonical observations;
- timestamps, units, values and provenance;
- reject unsupported / invalid records.

### Service
- incremental cursor / watermark handling;
- idempotency;
- persistence orchestration;
- ingestion health.

If the WUR ingestion work lands first, reuse its generic ingestion/storage contracts rather than duplicating them.

---

## 9. Persistence

V0 should reuse the existing application persistence where practical.

Add only the minimum state needed for live ingestion, such as:

- configured external source;
- upstream cursor / latest entry identity;
- ingestion status / last success / last error;
- canonical observations.

Do not store raw HTTP payloads indefinitely unless they prove useful. Small diagnostic payloads can be logged or retained temporarily, while canonical observations remain the durable product-facing record.

---

## 10. Testing

### Unit tests

- field mapping;
- timestamp parsing;
- unit handling;
- malformed / null values;
- unknown fields;
- provenance construction.

### Integration tests

Using deterministic saved ThingSpeak JSON fixtures:

- initial import creates expected observations;
- second overlapping import creates no duplicates;
- later entries append correctly;
- missing field values do not create fabricated observations;
- stale-source status changes correctly;
- temporary HTTP failure preserves previously ingested state.

### Optional manual smoke test

A command can poll the selected public channel for several minutes and demonstrate that new values appear in the application when the upstream feed changes.

The public endpoint must never be required for CI.

---

## 11. UI / product surface

Keep the UI change deliberately small.

For a live greenhouse show:

- source type: live / external;
- latest observation timestamp;
- freshness / stale state;
- environmental history from canonical observations;
- no simulation controls.

The most important product invariant is that simulated, replayed and live greenhouses remain visually and behaviorally distinct where their capabilities differ.

---

## 12. Implementation phases

### Phase 0 — inspect and freeze one public channel

- choose one currently active public greenhouse channel;
- document field meanings, units and cadence;
- capture a small response fixture;
- verify API limits / terms relevant to polling;
- define explicit mappings.

**Done when:** the source can be understood without relying on assumptions from chart labels alone.

### Phase 1 — one-shot ingestion

- implement client + mapper;
- import a bounded historical window;
- persist canonical observations with provenance;
- expose them through the existing greenhouse/history API.

**Done when:** a real ThingSpeak history is visible through Greenhouse Insights without simulation-specific code.

### Phase 2 — incremental live polling

- add cursor/watermark;
- idempotent overlap polling;
- source health/freshness;
- one-shot and continuous development commands.

**Done when:** the app stays up to date for several hours without duplicates or silent gaps.

### Phase 3 — minimal live UI

- clearly label the greenhouse as live/external;
- show freshness and latest timestamp;
- hide simulation-only actions;
- plot selected live observations.

**Done when:** a user can distinguish current, stale and historical live data at a glance.

### Phase 4 — hardening / extraction of reusable boundary

Only after ThingSpeak and WUR have both exercised ingestion:

- identify truly common source contracts;
- consolidate duplicated ingestion health / provenance logic;
- document how a future professional sensor gateway plugs in.

Do not generalize this boundary before there are at least two concrete data sources.

---

## 13. Definition of done for the experiment

The ThingSpeak experiment is successful when:

1. Greenhouse Insights can ingest a real public greenhouse feed continuously for at least several hours;
2. observations are canonical, timestamp-based, source-traceable and idempotent;
3. stale / missing data is visible rather than silently treated as current truth;
4. existing state/history surfaces can consume the data without ThingSpeak-specific branches;
5. no live network call is required by tests or CI;
6. removing the ThingSpeak adapter would not affect the core domain model;
7. the implementation makes the next read-only professional greenhouse integration easier.

---

## 14. Strategic role

ThingSpeak should remain a **low-cost live plumbing test**.

It validates:

- continuously arriving external data;
- timestamps and freshness;
- ingestion reliability;
- provenance;
- live-vs-simulation product behavior.

It does **not** validate:

- professional grower needs;
- commercial sensor quality;
- plant-level longitudinal sensing;
- useful agronomic recommendations;
- willingness to pay.

The next meaningful step after this remains access to a real research or commercial greenhouse stream, ideally combining environmental data with regular crop imagery.
