# Design and implementation plans

This directory contains current design/implementation plans. New implementation plans use a numeric prefix to make intended execution order visible without relying on file dates.

## Naming convention

Use two-digit prefixes with gaps so priorities can change without renaming every file:

```text
10_<plan>.md
20_<plan>.md
30_<plan>.md
```

The number is **implementation order, not architectural importance**. A plan may contain independently executable tracks and may overlap another plan when dependencies allow it. Completed plans can be archived rather than preserving a permanent global sequence.

Existing unnumbered documents predate this convention. Do not rename them solely to add a number: they are already linked from the README, technical reference, PRs and each other. Rename/move them only when there is a substantive reason, updating references in the same change.

## Current order

| Order | Plan | Status / role |
| --- | --- | --- |
| existing | `wur_execution_plan.md` | Active execution record for WUR ingestion/infrastructure work; several tracks already completed or underway. |
| existing | `wur_real_data_ingestion_replay_plan.md` | Architectural/source plan underlying the WUR vertical slice. |
| **10** | `10_unified_greenhouse_interface_plan.md` | Next product/domain convergence: one temporal decision interface for simulation, replay and future live operation. |
| **20** | ThingSpeak live ingestion (PR #8; rename to `20_thingspeak_live_ingestion_plan.md` when that plan is next touched/merged) | Small read-only live-source plumbing test. It should plug into the common interface rather than create a third dashboard. |
| existing | `infrastructure_update_plan.md` | Platform/deployment work; can proceed when required by deployment dependencies. |
| existing | `authentication_authorization_plan.md` | Authentication/authorization implementation is substantially complete; provider setup remains deployment work. |

## Ordering rule

Prefer finishing the smallest prerequisite that keeps the product model coherent. In particular, establish the common simulation/replay interface before implementing enough ThingSpeak UI to accidentally create a separate "live dashboard". Source ingestion itself can still proceed independently when it does not force UI/domain abstractions.
