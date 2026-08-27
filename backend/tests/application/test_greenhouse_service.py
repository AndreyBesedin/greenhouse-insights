from sqlalchemy import Engine

from application.bootstrap import bootstrap_greenhouses
from application.greenhouse_service import GreenhouseService
from domain.enums import SimulationStatus, SourceType


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
