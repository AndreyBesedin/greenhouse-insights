from datetime import UTC, datetime

from sqlalchemy import Engine

from application.persistence.management_trace_repository import ManagementTraceRepository
from domain.management_trace import ManagementTrace

TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _trace(day: int) -> ManagementTrace:
    return ManagementTrace(
        simulation_id="sim_gh_001",
        greenhouse_id="gh_001",
        simulated_day=day,
        provider="fake",
        model="scripted-v1",
        started_at=TIMESTAMP,
        completed_at=TIMESTAMP,
    )


def test_save_then_list_round_trips_traces_in_day_order(engine: Engine) -> None:
    repo = ManagementTraceRepository(engine)
    repo.save(_trace(3))
    repo.save(_trace(1))
    repo.save(_trace(2))

    traces = repo.list_for_simulation("sim_gh_001")

    assert [t.simulated_day for t in traces] == [1, 2, 3]


def test_list_for_simulation_returns_empty_when_nothing_saved(engine: Engine) -> None:
    repo = ManagementTraceRepository(engine)

    assert repo.list_for_simulation("does_not_exist") == []


def test_save_overwrites_the_same_day(engine: Engine) -> None:
    repo = ManagementTraceRepository(engine)
    repo.save(_trace(1))

    updated = _trace(1).model_copy(update={"requested_action_count": 5})
    repo.save(updated)

    traces = repo.list_for_simulation("sim_gh_001")
    assert len(traces) == 1
    assert traces[0].requested_action_count == 5


def test_delete_for_simulation_removes_all_of_that_simulations_traces(engine: Engine) -> None:
    repo = ManagementTraceRepository(engine)
    repo.save(_trace(1))
    repo.save(_trace(2))
    other = _trace(1).model_copy(update={"simulation_id": "sim_gh_002"})
    repo.save(other)

    repo.delete_for_simulation("sim_gh_001")

    assert repo.list_for_simulation("sim_gh_001") == []
    assert len(repo.list_for_simulation("sim_gh_002")) == 1
