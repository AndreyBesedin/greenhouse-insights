"""One deterministic end-to-end (Level B) eval case.

Per docs/design/domain_model_eval_refactor_plan.md PR 3: Level A cases
(test_metrics.py, management/evaluation/cases.py) build the smallest
realistic observation set and reconstruct from it. This is the
complementary Level B case - a fixed seed/config run through the real
simulator/observation/reconstruction/policy pipeline
(simulation.runner.SimulationRunner, exactly what the application uses),
checked against both the observable recommendation and the hidden
simulator truth. The hidden truth (GreenhouseWorld, via WorldRepository) is
read only here, by the evaluator - never passed into policy.decide() or any
management context.
"""

from datetime import UTC, date, datetime

from sqlalchemy import Engine

from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from simulation.definitions import SimulationDefinition
from simulation.runner import SimulationRunner
from simulation.scenarios import SCENARIO_REGISTRY

GREENHOUSE_ID = "gh_eval_e2e"
PLANT_ID = f"{GREENHOUSE_ID}_plant_001"
SIMULATION_ID = "sim_eval_e2e"
# gh_002's dynamics reliably cross the watering trigger on day 2, not day 1
# (also relied on by tests/application/test_api_recommendations.py) - a
# real, non-fabricated signal from the simulator rather than a hand-picked
# threshold.
CONFIG = SCENARIO_REGISTRY["gh_002"].model_copy(
    update={"greenhouse_id": GREENHOUSE_ID, "columns": 1, "rows": 1}
)


def _seed(engine: Engine) -> None:
    greenhouse = Greenhouse(
        greenhouse_id=GREENHOUSE_ID,
        name="End-to-end eval greenhouse",
        description="",
        source_type=SourceType.SIMULATION,
        layout=GreenhouseLayout(rows=1, columns=1),
        plants=[Plant(plant_id=PLANT_ID, variety=CONFIG.variety, row=1, position_in_row=1)],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    GreenhouseRepository(engine).save(greenhouse)
    ScenarioConfigRepository(engine).save(CONFIG)
    SimulationRepository(engine).save(
        SimulationDefinition(
            simulation_id=SIMULATION_ID,
            greenhouse_id=GREENHOUSE_ID,
            scenario_definition=GREENHOUSE_ID,
            start_date=date(2026, 1, 1),
            duration_days=CONFIG.duration_days,
            random_seed=CONFIG.random_seed,
            total_steps=CONFIG.duration_days,
        )
    )


def test_low_moisture_day_reliably_proposes_watering(engine: Engine) -> None:
    _seed(engine)
    runner = SimulationRunner(engine, step_delay_seconds=0)

    day_1 = runner.prepare_day(SIMULATION_ID, 1)
    assert not any(a.action_type == "WATER_PLANT" for a in day_1.proposed_actions)

    day_2 = runner.prepare_day(SIMULATION_ID, 2)

    watering = [a for a in day_2.proposed_actions if a.action_type == "WATER_PLANT"]
    assert len(watering) == 1
    assert watering[0].plant_id == PLANT_ID

    # Cross-check against hidden simulator truth - never seen by the policy,
    # read here only to confirm the recommendation is actually warranted.
    world = WorldRepository(engine).get_latest(GREENHOUSE_ID)
    assert world is not None
    plant_world = world.plant(PLANT_ID)
    reservoir_pct = 100.0 * plant_world.water_reservoir_ml / CONFIG.water_capacity_ml
    assert reservoir_pct < CONFIG.watering_trigger_reservoir_pct
