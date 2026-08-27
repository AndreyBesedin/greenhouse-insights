from datetime import UTC, datetime

from sqlalchemy import Engine

from application.bootstrap import bootstrap_greenhouses
from application.greenhouse_service import GreenhouseService
from application.persistence.state_repository import StateRepository
from domain.enums import PlantHealth, SimulationStatus, SourceType
from domain.state import GreenhouseState, PlantState


def test_list_greenhouses_returns_both_seeded_greenhouses(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    items = service.list_greenhouses()

    assert {item.greenhouse_id for item in items} == {"gh_001", "gh_002"}


def test_list_greenhouses_reports_plant_count_crop_and_not_started_status(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    items = {item.greenhouse_id: item for item in service.list_greenhouses()}
    gh_001 = items["gh_001"]

    assert gh_001.plant_count == 40
    assert gh_001.crop == "cherry_tomato"
    assert gh_001.source_type == SourceType.SIMULATION
    assert gh_001.status == SimulationStatus.NOT_STARTED
    assert gh_001.current_step == 0
    assert gh_001.total_steps == 28


def test_get_greenhouse_detail_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine)

    assert service.get_greenhouse_detail("does_not_exist") is None


def test_get_greenhouse_detail_embeds_full_greenhouse_and_simulation_summary(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    detail = service.get_greenhouse_detail("gh_001")

    assert detail is not None
    assert len(detail.greenhouse.plants) == 40
    assert detail.simulation.simulation_id == "sim_gh_001"
    assert detail.simulation.status == SimulationStatus.NOT_STARTED
    assert detail.simulation.total_steps == 28


def _save_state(engine: Engine, greenhouse_id: str, day: int) -> None:
    plant_state = PlantState(
        plant_id=f"{greenhouse_id}_plant_001",
        greenhouse_id=greenhouse_id,
        simulated_day=day,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        health=PlantHealth.HEALTHY,
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            simulated_day=day,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            plant_states=[plant_state],
        )
    )


def test_get_state_returns_the_latest_snapshot_when_no_day_given(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)
    service = GreenhouseService(engine)

    state = service.get_state("gh_001", day=None)

    assert state is not None
    assert state.simulated_day == 8


def test_get_state_returns_a_specific_day_when_given(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)
    service = GreenhouseService(engine)

    state = service.get_state("gh_001", day=5)

    assert state is not None
    assert state.simulated_day == 5


def test_get_state_returns_none_when_no_snapshot_exists_for_that_day(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    assert service.get_state("gh_001", day=3) is None


def test_get_plant_detail_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine)

    assert service.get_plant_detail("does_not_exist", "plant_001", day=None) is None


def test_get_plant_detail_returns_none_for_unknown_plant(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    assert service.get_plant_detail("gh_001", "does_not_exist", day=None) is None


def test_get_plant_detail_returns_plant_config_with_no_state_before_simulation_starts(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine)

    detail = service.get_plant_detail("gh_001", "gh_001_plant_001", day=None)

    assert detail is not None
    assert detail.plant.plant_id == "gh_001_plant_001"
    assert detail.state is None


def test_get_plant_detail_includes_that_plants_state_once_it_exists(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    service = GreenhouseService(engine)

    detail = service.get_plant_detail("gh_001", "gh_001_plant_001", day=5)

    assert detail is not None
    assert detail.state is not None
    assert detail.state.simulated_day == 5
    assert detail.state.health == PlantHealth.HEALTHY
