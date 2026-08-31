# Agent Guidance

## Design documents

All design documents for this project live in `docs/design/`. Before making
non-trivial changes to product behavior, domain model, or the simulation
engine, check that folder for relevant context:

- `greenhouse_intelligence_poc_brief.md` — overall product scope and vision.
- `greenhouse_simulation_design.md` — design of the simulation engine (hidden
  world model, observation generation, scenario evolution).
- `greenhouse_agentic_management_design.md` — design of the agentic management
  layer (policy interface, agent tools, action validation, evaluation).
- `greenhouse_ui_initial_brief.md` — initial brief for the frontend UI/UX.

New design docs should be added to `docs/design/` rather than the repo root,
so this stays the single place to look for them.

See also `DEVELOPMENT_GUIDELINES.md` for how the project is built day to day
(coding conventions, repo layout, build order).
