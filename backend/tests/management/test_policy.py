from datetime import UTC, datetime

from domain.enums import PlantHealth
from domain.state import PlantState
from management.context import GreenhouseManagementContext
from management.policy import NoOpPolicy
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
