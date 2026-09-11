from datetime import datetime

from pydantic import BaseModel

from domain.enums import (
    ActionExecutorType,
    ApprovalSource,
    ManagementPolicyType,
    RecommendationStatus,
)
from domain.provenance import RecordSource
from management.validation.actions import RequestedAction


class Recommendation(BaseModel):
    """A persisted, reviewable proposal - the human-in-the-loop counterpart
    to a bare RequestedAction (docs/archive/design-history/demo_readiness_plan.md sections
    10-11). The management policy still only ever proposes; this is what
    the application layer turns that proposal into so a human can approve
    or dismiss it before anything in the world changes.

    requested_by is source_policy (which policy proposed this) rather than
    a separate field - it already carries that meaning. approved_by and
    executed_by are the new provenance section 7 asks for: who signed off,
    and what actually carried the action out. source is a different kind
    of provenance - which system/run produced the recommendation (today
    always a simulation run) - kept separate from simulation identity so a
    Recommendation stays valid for live operation too
    (docs/archive/design-history/domain_model_eval_refactor_plan.md, PR 1).
    """

    recommendation_id: str
    source: RecordSource
    greenhouse_id: str
    # The timestamp of the observable state this proposal was made against
    # - the GreenhouseState snapshot the policy saw. Ties a recommendation
    # to a point in the greenhouse's own chronology rather than to a
    # simulation day counter (docs/design/wur_real_data_ingestion_replay_plan.md
    # section 9).
    context_timestamp: datetime
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
