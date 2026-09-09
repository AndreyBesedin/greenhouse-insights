# Design history archive

The documents in this folder are retained for decision traceability - they
record the reasoning, trade-offs, and sequence of decisions that shaped this
project's architecture.

They are **historical snapshots, not current source-of-truth
documentation**. Where an archived document conflicts with the implemented
system, the code, tests, `README.md`, and `docs/technical_reference.md`
take precedence.

Archived per `docs/archive/design-history/domain_model_eval_refactor_plan.md`
PR 4, once the refactor/eval stack it describes (PRs 1-3) was complete:

- `greenhouse_intelligence_poc_brief.md` - original product scope and vision.
- `greenhouse_simulation_design.md` - original design of the simulation engine.
- `greenhouse_agentic_management_design.md` - original design of the agentic
  management layer.
- `greenhouse_ui_initial_brief.md` - initial brief for the frontend UI/UX.
- `demo_readiness_plan.md` - the demo-readiness implementation plan referenced
  throughout the codebase's docstrings/comments as design rationale.
- `domain_model_eval_refactor_plan.md` - the refactor plan that produced this
  archive.

Code comments and docstrings across the codebase still cite these documents
by path (e.g. "docs/archive/design-history/greenhouse_agentic_management_design.md
§35") as rationale for why a piece of code is shaped the way it is - that
remains a valid use of them. Treat them as you would a citation to a design
doc or RFC: useful context for *why*, not a live specification of *what the
system currently does*.
