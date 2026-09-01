from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ToolCallTrace(BaseModel):
    tool: str
    args: dict[str, Any]
    summary: str


class ManagementTrace(BaseModel):
    simulation_id: str
    greenhouse_id: str
    simulated_day: int
    provider: str
    model: str
    tool_calls: list[ToolCallTrace] = []
    requested_action_count: int = 0
    accepted_action_count: int = 0
    rejected_action_count: int = 0
    status: Literal["SUCCESS", "FAILED"] = "SUCCESS"
    error: str | None = None
    started_at: datetime
    completed_at: datetime
