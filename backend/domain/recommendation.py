from datetime import datetime

from pydantic import BaseModel

from domain.enums import (
    ActionExecutorType,
    ApprovalSource,
    ManagementPolicyType,
    RecommendationStatus,
)
from management.validation.actions import RequestedAction


class Recommendation(BaseModel):
    """A persisted, reviewable proposal - the human-in-the-loop counterpart
    to a bare RequestedAction (docs/design/demo_readiness_plan.md sections
    10-11). The management policy still only ever proposes; this is what
    the application layer turns that proposal into so a human can approve
    or dismiss it before anything in the world changes.

    requested_by is source_policy (which policy proposed this) rather than
    a separate field - it already carries that meaning. approved_by and
    executed_by are the new provenance section 7 asks for: who signed off,
    and what actually carried the action out.
    """

    recommendation_id: str
    simulation_id: str
    greenhouse_id: str
    simulated_day: int
    plant_id: str

    action: RequestedAction
    source_policy: ManagementPolicyType

    status: RecommendationStatus = RecommendationStatus.PENDING
    reason: str
    evidence: dict[str, float | int | str | None] = {}
    rejection_reason: str | None = None

    approved_by: ApprovalSource | None = None
    executed_by: ActionExecutorType | None = None

    requested_at: datetime
    reviewed_at: datetime | None = None
    executed_at: datetime | None = None
