from typing import Literal

from pydantic import BaseModel


class ManagementProgress(BaseModel):
    """High-level, structured progress for an in-flight agentic day
    analysis - docs/design/demo_readiness_plan.md section 14. Never carries
    chain-of-thought, only tool-call-derived milestones (Inspecting Plant X,
    Checking Plant X history, ...) so a real LLM call does not look like a
    frozen UI while it runs."""

    simulation_id: str
    simulated_day: int
    phase: Literal["ANALYZING", "READY"]
    message: str
    plant_id: str | None = None
    completed_tool_calls: int = 0
    recommendation_count: int | None = None
