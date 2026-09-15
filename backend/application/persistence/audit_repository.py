import json

from sqlalchemy import Engine, select
from sqlalchemy.engine import RowMapping

from application.auth.audit import AuditAction, AuditEvent
from application.persistence.schema import audit_events
from application.persistence.timestamps import from_db_timestamp, to_db_timestamp


class AuditRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(self, event: AuditEvent) -> None:
        row = {
            "audit_id": event.audit_id,
            "timestamp": to_db_timestamp(event.timestamp),
            "actor_id": event.actor_id,
            "action": event.action.value,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "organization_id": event.organization_id,
            "details_json": json.dumps(event.details, sort_keys=True),
        }
        with self._engine.begin() as connection:
            connection.execute(audit_events.insert().values(**row))

    def list_recent(self, *, limit: int = 200) -> list[AuditEvent]:
        statement = select(audit_events).order_by(audit_events.c.timestamp.desc()).limit(limit)
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_event(row) for row in rows]

    def list_for_organization(self, organization_id: str, *, limit: int = 200) -> list[AuditEvent]:
        statement = (
            select(audit_events)
            .where(audit_events.c.organization_id == organization_id)
            .order_by(audit_events.c.timestamp.desc())
            .limit(limit)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_event(row) for row in rows]


def _row_to_event(mapping: RowMapping) -> AuditEvent:
    return AuditEvent(
        audit_id=mapping["audit_id"],
        timestamp=from_db_timestamp(mapping["timestamp"]),
        actor_id=mapping["actor_id"],
        action=AuditAction(mapping["action"]),
        target_type=mapping["target_type"],
        target_id=mapping["target_id"],
        organization_id=mapping["organization_id"],
        details=json.loads(mapping["details_json"]),
    )
