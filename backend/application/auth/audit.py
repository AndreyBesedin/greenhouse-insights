"""The audit trail for privileged mutations: who did what to which
resource, when (docs/design/infrastructure_update_plan.md section 8).
Records carry enough context to reconstruct a change without storing
secrets; they are append-only and never edited by the application.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AuditAction(StrEnum):
    ORGANIZATION_CREATED = "ORGANIZATION_CREATED"
    MEMBERSHIP_SET = "MEMBERSHIP_SET"
    MEMBERSHIP_REMOVED = "MEMBERSHIP_REMOVED"
    PLATFORM_ADMIN_GRANTED = "PLATFORM_ADMIN_GRANTED"
    PLATFORM_ADMIN_REVOKED = "PLATFORM_ADMIN_REVOKED"
    GREENHOUSE_CREATED = "GREENHOUSE_CREATED"
    GREENHOUSE_DELETED = "GREENHOUSE_DELETED"
    GREENHOUSE_REASSIGNED = "GREENHOUSE_REASSIGNED"


class AuditEvent(BaseModel):
    audit_id: str
    timestamp: datetime
    # The user id of who acted; "system:bootstrap" when the platform
    # itself acted from configuration rather than a signed-in user.
    actor_id: str
    action: AuditAction
    # What was acted on: "organization", "membership", "user", "greenhouse".
    target_type: str
    target_id: str
    # The tenant the change concerns, when there is one.
    organization_id: str | None = None
    # Before/after context, plain JSON, no secrets.
    details: dict[str, Any] = Field(default_factory=dict)
