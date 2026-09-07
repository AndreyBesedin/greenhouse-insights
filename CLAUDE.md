# Agent Guidance

## Design documents

The original design documents for this project have been archived to
`docs/archive/design-history/` (see that folder's `README.md`) now that the
domain-model/eval refactor they described is complete - they are historical
snapshots, not current specifications. For current, maintained reference
documentation, see `README.md` and `docs/technical_reference.md`.

Code comments/docstrings across the codebase still cite the archived docs by
path (e.g. `docs/archive/design-history/greenhouse_agentic_management_design.md
§35`) as rationale for why something is shaped the way it is - that remains
useful context for *why*, not a live spec of *what the system currently
does*. Where an archived doc conflicts with the implemented system, the
code, tests, and current reference docs take precedence.

New design/planning docs for future work should go in `docs/design/`
(recreate the folder if it doesn't exist) rather than the repo root, so
there is one place to look for active design work; archive them to
`docs/archive/design-history/` once they stop being the active
specification, following the same pattern.

See also `DEVELOPMENT_GUIDELINES.md` for how the project is built day to day
(coding conventions, repo layout, build order).
