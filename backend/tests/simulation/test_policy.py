from datetime import UTC, datetime

from domain.enums import PlantHealth
from domain.state import PlantState
from simulation.actions import HarvestPlantAction, LowerPlantAction, WaterPlantAction
from simulation.agent.context import GreenhouseManagementContext
from simulation.policy import DeterministicPolicy, NoOpPolicy
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_ID = "gh_001_plant_001"
TIMESTAMP = datetime(2026, 1, 9, tzinfo=UTC)


def _context(**overrides: object) -> GreenhouseManagementContext:
    defaults: dict[str, object] = dict(
        plant_id=PLANT_ID,
        greenhouse_id="gh_001",
        simulated_day=1,
        timestamp=TIMESTAMP,
        health=PlantHealth.HEALTHY,
        latest_soil_moisture_pct=80.0,
    )
    defaults.update(overrides)
    plant_state = PlantState(**defaults)
    return GreenhouseManagementContext(greenhouse_id="gh_001", day=1, plant_states=[plant_state])


def test_no_op_policy_never_requests_actions() -> None:
    assert NoOpPolicy().decide(_context(), CONFIG) == []


def test_deterministic_policy_waters_a_plant_with_low_soil_moisture() -> None:
    context = _context(latest_soil_moisture_pct=0.0)

    actions = DeterministicPolicy().decide(context, CONFIG)

    assert any(isinstance(a, WaterPlantAction) and a.plant_id == PLANT_ID for a in actions)


def test_deterministic_policy_does_not_water_a_well_watered_plant() -> None:
    context = _context(latest_soil_moisture_pct=90.0)

    actions = DeterministicPolicy().decide(context, CONFIG)

    assert not any(isinstance(a, WaterPlantAction) for a in actions)


def test_deterministic_policy_harvests_once_enough_fruit_is_ripe() -> None:
    context = _context(
        latest_ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
        latest_soil_moisture_pct=90.0,
    )

    actions = DeterministicPolicy().decide(context, CONFIG)

    assert any(isinstance(a, HarvestPlantAction) and a.plant_id == PLANT_ID for a in actions)


def test_deterministic_policy_lowers_a_tall_plant() -> None:
    context = _context(
        latest_visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 10,
        latest_soil_moisture_pct=90.0,
    )

    actions = DeterministicPolicy().decide(context, CONFIG)

    assert any(isinstance(a, LowerPlantAction) and a.plant_id == PLANT_ID for a in actions)


def test_deterministic_policy_ignores_plants_with_no_readings() -> None:
    context = _context(latest_soil_moisture_pct=None)

    assert DeterministicPolicy().decide(context, CONFIG) == []
