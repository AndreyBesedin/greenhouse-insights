from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.recommendation_repository import RecommendationRepository
from domain.enums import (
    ActionExecutorType,
    ApprovalSource,
    ManagementPolicyType,
    RecommendationStatus,
    SourceType,
)
from domain.provenance import RecordSource
from domain.recommendation import Recommendation
from management.validation.actions import WaterPlantAction

TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _recommendation(
    recommendation_id: str = "rec_1", day: int = 1, **overrides: object
) -> Recommendation:
    defaults: dict[str, object] = dict(
        recommendation_id=recommendation_id,
        source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_001"),
        greenhouse_id="gh_001",
        simulated_day=day,
        plant_id="gh_001_plant_001",
        action=WaterPlantAction(plant_id="gh_001_plant_001", amount_ml=700),
        source_policy=ManagementPolicyType.DETERMINISTIC,
        reason="Soil moisture at 12%.",
        evidence={"soil_moisture_pct": 12.0},
        requested_at=TIMESTAMP,
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def test_save_then_get_round_trips_a_recommendation(engine: Engine) -> None:
    repo = RecommendationRepository(engine)
    repo.save(_recommendation())

    result = repo.get("rec_1")

    assert result is not None
    assert result.recommendation_id == "rec_1"
    assert isinstance(result.action, WaterPlantAction)
    assert result.action.amount_ml == 700
    assert result.status == RecommendationStatus.PENDING
    assert result.evidence == {"soil_moisture_pct": 12.0}


def test_get_returns_none_for_unknown_recommendation(engine: Engine) -> None:
    repo = RecommendationRepository(engine)

    assert repo.get("does_not_exist") is None


def test_save_overwrites_the_same_recommendation_by_id(engine: Engine) -> None:
    repo = RecommendationRepository(engine)
    repo.save(_recommendation())

    approved = _recommendation().model_copy(
        update={
            "status": RecommendationStatus.EXECUTED,
            "approved_by": ApprovalSource.HUMAN,
            "executed_by": ActionExecutorType.SIMULATED_OPERATOR,
            "reviewed_at": TIMESTAMP,
            "executed_at": TIMESTAMP,
        }
    )
    repo.save(approved)

    result = repo.get("rec_1")
    assert result is not None
    assert result.status == RecommendationStatus.EXECUTED
    assert result.approved_by == ApprovalSource.HUMAN
    assert result.executed_by == ActionExecutorType.SIMULATED_OPERATOR


def test_list_for_day_returns_only_that_greenhouse_and_day_in_requested_order(
    engine: Engine,
) -> None:
    repo = RecommendationRepository(engine)
    repo.save(_recommendation("rec_1", day=1, requested_at=TIMESTAMP))
    repo.save(
        _recommendation(
            "rec_2",
            day=1,
            plant_id="gh_001_plant_002",
            requested_at=datetime(2026, 1, 9, 0, 1, tzinfo=UTC),
        )
    )
    repo.save(_recommendation("rec_3", day=2))
    repo.save(
        _recommendation(
            "rec_4",
            day=1,
            greenhouse_id="gh_002",
            source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_002"),
        )
    )

    result = repo.list_for_day("gh_001", 1)

    assert [r.recommendation_id for r in result] == ["rec_1", "rec_2"]


def test_list_pending_for_day_excludes_resolved_recommendations(engine: Engine) -> None:
    repo = RecommendationRepository(engine)
    repo.save(_recommendation("rec_1", day=1))
    repo.save(
        _recommendation("rec_2", day=1, plant_id="gh_001_plant_002").model_copy(
            update={"status": RecommendationStatus.DISMISSED, "reviewed_at": TIMESTAMP}
        )
    )

    result = repo.list_pending_for_day("gh_001", 1)

    assert [r.recommendation_id for r in result] == ["rec_1"]


def test_delete_for_greenhouse_removes_only_that_greenhouses_recommendations(
    engine: Engine,
) -> None:
    repo = RecommendationRepository(engine)
    repo.save(_recommendation("rec_1"))
    repo.save(
        _recommendation(
            "rec_2",
            greenhouse_id="gh_002",
            source=RecordSource(type=SourceType.SIMULATION, source_id="sim_gh_002"),
        )
    )

    repo.delete_for_greenhouse("gh_001")

    assert repo.list_for_day("gh_001", 1) == []
    assert len(repo.list_for_day("gh_002", 1)) == 1
