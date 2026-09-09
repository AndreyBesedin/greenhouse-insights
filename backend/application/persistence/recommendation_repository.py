import json
from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import RowMapping

from application.persistence.schema import recommendations
from domain.enums import RecommendationStatus
from domain.provenance import RecordSource
from domain.recommendation import Recommendation
from management.validation.actions import RequestedAction

_ACTION_ADAPTER: TypeAdapter[RequestedAction] = TypeAdapter(RequestedAction)


class RecommendationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, recommendation: Recommendation) -> None:
        row = _recommendation_to_row(recommendation)
        statement = insert(recommendations).values(**row)
        statement = statement.on_conflict_do_update(
            index_elements=["recommendation_id"],
            set_={key: value for key, value in row.items() if key != "recommendation_id"},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get(self, recommendation_id: str) -> Recommendation | None:
        statement = select(recommendations).where(
            recommendations.c.recommendation_id == recommendation_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        return None if row is None else _row_to_recommendation(row)

    def list_for_day(self, greenhouse_id: str, day: int) -> list[Recommendation]:
        statement = (
            select(recommendations)
            .where(recommendations.c.greenhouse_id == greenhouse_id)
            .where(recommendations.c.simulated_day == day)
            .order_by(recommendations.c.requested_at)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_recommendation(row) for row in rows]

    def list_pending_for_day(self, greenhouse_id: str, day: int) -> list[Recommendation]:
        return [
            r
            for r in self.list_for_day(greenhouse_id, day)
            if r.status == RecommendationStatus.PENDING
        ]

    def delete_for_greenhouse(self, greenhouse_id: str) -> None:
        statement = delete(recommendations).where(recommendations.c.greenhouse_id == greenhouse_id)
        with self._engine.begin() as connection:
            connection.execute(statement)


def _recommendation_to_row(recommendation: Recommendation) -> dict[str, object]:
    return {
        "recommendation_id": recommendation.recommendation_id,
        "greenhouse_id": recommendation.greenhouse_id,
        "simulated_day": recommendation.simulated_day,
        "plant_id": recommendation.plant_id,
        "action_json": recommendation.action.model_dump_json(),
        "source_type": recommendation.source.type.value,
        "source_id": recommendation.source.source_id,
        "source_policy": recommendation.source_policy.value,
        "status": recommendation.status.value,
        "reason": recommendation.reason,
        "evidence_json": json.dumps(recommendation.evidence),
        "rejection_reason": recommendation.rejection_reason,
        "approved_by": recommendation.approved_by.value if recommendation.approved_by else None,
        "executed_by": recommendation.executed_by.value if recommendation.executed_by else None,
        "requested_at": recommendation.requested_at.isoformat(),
        "reviewed_at": recommendation.reviewed_at.isoformat()
        if recommendation.reviewed_at
        else None,
        "executed_at": recommendation.executed_at.isoformat()
        if recommendation.executed_at
        else None,
    }


def _row_to_recommendation(mapping: RowMapping) -> Recommendation:
    return Recommendation(
        recommendation_id=mapping["recommendation_id"],
        source=RecordSource(type=mapping["source_type"], source_id=mapping["source_id"]),
        greenhouse_id=mapping["greenhouse_id"],
        simulated_day=mapping["simulated_day"],
        plant_id=mapping["plant_id"],
        action=_ACTION_ADAPTER.validate_json(mapping["action_json"]),
        source_policy=mapping["source_policy"],
        status=mapping["status"],
        reason=mapping["reason"],
        evidence=json.loads(mapping["evidence_json"]),
        rejection_reason=mapping["rejection_reason"],
        approved_by=mapping["approved_by"],
        executed_by=mapping["executed_by"],
        requested_at=datetime.fromisoformat(mapping["requested_at"]),
        reviewed_at=datetime.fromisoformat(mapping["reviewed_at"])
        if mapping["reviewed_at"]
        else None,
        executed_at=datetime.fromisoformat(mapping["executed_at"])
        if mapping["executed_at"]
        else None,
    )
