from sqlalchemy import Engine

from application.bootstrap import bootstrap_greenhouses
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.simulation_repository import SimulationRepository
from domain.enums import SimulationStatus


def test_bootstrap_seeds_a_greenhouse_and_simulation_per_registry_entry(engine: Engine) -> None:
    bootstrap_greenhouses(engine)

    greenhouses = GreenhouseRepository(engine).list()
    assert {gh.greenhouse_id for gh in greenhouses} == {"gh_001", "gh_002"}


def test_bootstrap_creates_the_right_plant_count_per_greenhouse(engine: Engine) -> None:
    bootstrap_greenhouses(engine)

    gh_001 = GreenhouseRepository(engine).get("gh_001")
    gh_002 = GreenhouseRepository(engine).get("gh_002")

    assert gh_001 is not None and len(gh_001.plants) == 40
    assert gh_002 is not None and len(gh_002.plants) == 1


def test_bootstrap_creates_a_not_started_simulation_definition_per_greenhouse(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)

    definition = SimulationRepository(engine).get("sim_gh_001")

    assert definition is not None
    assert definition.status == SimulationStatus.NOT_STARTED
    assert definition.total_steps == 28


def test_bootstrap_is_idempotent_and_preserves_simulation_progress(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    sim_repo = SimulationRepository(engine)
    definition = sim_repo.get("sim_gh_001")
    assert definition is not None
    progressed = definition.model_copy(
        update={"current_step": 5, "status": SimulationStatus.RUNNING}
    )
    sim_repo.save(progressed)

    bootstrap_greenhouses(engine)

    reloaded = sim_repo.get("sim_gh_001")
    assert reloaded is not None
    assert reloaded.current_step == 5
    assert reloaded.status == SimulationStatus.RUNNING
    assert len(GreenhouseRepository(engine).list()) == 2
