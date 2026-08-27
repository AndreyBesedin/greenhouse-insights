from datetime import date, timedelta

from domain.enums import SimulationStatus
from simulation.definitions import SimulationDefinition


def _make_definition(**overrides: object) -> SimulationDefinition:
    defaults: dict[str, object] = dict(
        simulation_id="sim_gh_001",
        greenhouse_id="gh_001",
        scenario_definition="gh_001",
        start_date=date(2026, 1, 1),
        duration_days=28,
        random_seed=1001,
        total_steps=28,
    )
    defaults.update(overrides)
    return SimulationDefinition(**defaults)


def test_simulation_definition_status_defaults_to_not_started() -> None:
    definition = _make_definition()

    assert definition.status == SimulationStatus.NOT_STARTED


def test_simulation_definition_current_step_defaults_to_zero() -> None:
    definition = _make_definition()

    assert definition.current_step == 0


def test_simulation_definition_step_duration_defaults_to_one_day() -> None:
    definition = _make_definition()

    assert definition.step_duration == timedelta(days=1)


def test_simulation_status_has_expected_members() -> None:
    assert {member.value for member in SimulationStatus} == {
        "NOT_STARTED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
    }
