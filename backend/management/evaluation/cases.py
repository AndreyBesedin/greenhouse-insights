"""Ground-truth eval cases for agent decision quality.

Per docs/design/greenhouse_agentic_management_design.md §35-37: each case
pairs an observable context (what any AgentModelProvider is allowed to see)
with a private expected outcome (§36) the provider never sees. Kept small
and provider-agnostic on purpose - these run against FakeAgentModelProvider
today and against a real provider unchanged later.
"""

from datetime import UTC, datetime

from pydantic import BaseModel

from domain.enums import PlantHealth
from domain.state import PlantState
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.scenarios.config import ScenarioConfig

CONFIG = SCENARIO_REGISTRY["gh_001"]
_TIMESTAMP = datetime(2026, 1, 20, tzinfo=UTC)


class EvalCase(BaseModel):
    case_id: str
    description: str
    plant_state: PlantState
    history: list[PlantState] = []
    config: ScenarioConfig = CONFIG
    expected_action_types: frozenset[str]
    """Exact set of action_type values a correct decision returns. Empty
    means "no action is the right call"."""
    param_ranges: dict[str, tuple[str, float, float]] = {}
    """action_type -> (field_name, min, max) for that action's primary
    numeric parameter, e.g. {"WATER_PLANT": ("amount_ml", 400.0, 900.0)}."""
    requires_investigation: bool
    """Whether a correct decision must call get_plant_history before
    acting - true for anything not already known HEALTHY (§9)."""


def _plant(plant_id: str = "eval_plant", **overrides: object) -> PlantState:
    defaults: dict[str, object] = dict(
        plant_id=plant_id,
        greenhouse_id="gh_eval",
        simulated_day=20,
        timestamp=_TIMESTAMP,
        health=PlantHealth.HEALTHY,
    )
    defaults.update(overrides)
    return PlantState(**defaults)


CASES: list[EvalCase] = [
    EvalCase(
        case_id="sustained_low_moisture_waters",
        description="Low soil moisture confirmed by sustained history should be watered - "
        "a single low reading is ambiguous and must be investigated first regardless of "
        "the plant's own condition, but a sustained one is not.",
        plant_state=_plant(latest_soil_moisture_pct=10.0),
        history=[_plant(latest_soil_moisture_pct=9.0)],
        expected_action_types=frozenset({"WATER_PLANT"}),
        param_ranges={"WATER_PLANT": ("amount_ml", 400.0, 900.0)},
        requires_investigation=True,
    ),
    EvalCase(
        case_id="healthy_well_watered_does_nothing",
        description="A healthy, well-watered plant with no other trigger needs no action.",
        plant_state=_plant(latest_soil_moisture_pct=85.0),
        expected_action_types=frozenset(),
        requires_investigation=False,
    ),
    EvalCase(
        case_id="healthy_ripe_fruit_harvests",
        description="A healthy plant with enough ripe fruit should be harvested.",
        plant_state=_plant(
            latest_soil_moisture_pct=85.0,
            latest_ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
        ),
        expected_action_types=frozenset({"HARVEST_PLANT"}),
        requires_investigation=False,
    ),
    EvalCase(
        case_id="healthy_tall_plant_lowers",
        description="A healthy plant taller than the threshold should be lowered.",
        plant_state=_plant(
            latest_soil_moisture_pct=85.0,
            latest_visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 15,
        ),
        expected_action_types=frozenset({"LOWER_PLANT"}),
        param_ranges={"LOWER_PLANT": ("amount_cm", 20.0, 60.0)},
        requires_investigation=False,
    ),
    EvalCase(
        case_id="multiple_triggers_all_act",
        description="A plant tripping all three mechanical thresholds at once should get "
        "all three actions - none should be missed. Harvest/lower are unambiguous and need "
        "no investigation; sustained low moisture does require it, same as watering alone.",
        plant_state=_plant(
            latest_soil_moisture_pct=5.0,
            latest_ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
            latest_visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 20,
        ),
        history=[_plant(latest_soil_moisture_pct=4.0)],
        expected_action_types=frozenset({"WATER_PLANT", "HARVEST_PLANT", "LOWER_PLANT"}),
        param_ranges={
            "WATER_PLANT": ("amount_ml", 400.0, 900.0),
            "LOWER_PLANT": ("amount_cm", 20.0, 60.0),
        },
        requires_investigation=True,
    ),
    EvalCase(
        case_id="monitor_single_low_reading_inspects_not_waters",
        description="A MONITOR plant with one low-moisture reading and no sustained "
        "history is ambiguous evidence - schedule inspection, do not water on a single "
        "noisy reading.",
        plant_state=_plant(health=PlantHealth.MONITOR, latest_soil_moisture_pct=12.0),
        history=[],
        expected_action_types=frozenset({"SCHEDULE_INSPECTION"}),
        requires_investigation=True,
    ),
    EvalCase(
        case_id="monitor_sustained_low_moisture_waters",
        description="A MONITOR plant whose history confirms sustained low moisture "
        "should be watered, not merely inspected.",
        plant_state=_plant(health=PlantHealth.MONITOR, latest_soil_moisture_pct=12.0),
        history=[_plant(latest_soil_moisture_pct=9.0)],
        expected_action_types=frozenset({"WATER_PLANT"}),
        param_ranges={"WATER_PLANT": ("amount_ml", 400.0, 900.0)},
        requires_investigation=True,
    ),
    EvalCase(
        case_id="non_healthy_condition_with_clean_readings_needs_no_action",
        description="A plant flagged non-healthy but with clean environmental readings "
        "needs no action and no investigation - condition and environment are different "
        "questions (docs/design/domain_model_eval_refactor_plan.md PR 2), and it is the "
        "evidence, not the health label, that decides whether a closer look is warranted.",
        plant_state=_plant(health=PlantHealth.ACTION_REQUIRED, latest_soil_moisture_pct=85.0),
        history=[_plant(latest_soil_moisture_pct=88.0)],
        expected_action_types=frozenset(),
        requires_investigation=False,
    ),
    EvalCase(
        case_id="monitor_sustained_low_moisture_and_ripe_fruit_both_act",
        description="Sustained low moisture and ripe fruit together should produce both "
        "a watering and a harvest - harvesting does not require investigation, watering "
        "does, and both must still be decided correctly in the same cycle.",
        plant_state=_plant(
            health=PlantHealth.MONITOR,
            latest_soil_moisture_pct=11.0,
            latest_ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
        ),
        history=[_plant(latest_soil_moisture_pct=10.0)],
        expected_action_types=frozenset({"WATER_PLANT", "HARVEST_PLANT"}),
        param_ranges={"WATER_PLANT": ("amount_ml", 400.0, 900.0)},
        requires_investigation=True,
    ),
    EvalCase(
        case_id="budget_exhausted_falls_back_to_inspection",
        description="When the tool-call budget is exhausted before a non-healthy plant "
        "can be investigated, the safe fallback is inspection - never guess and water.",
        plant_state=_plant(health=PlantHealth.ACTION_REQUIRED, latest_soil_moisture_pct=8.0),
        config=CONFIG.model_copy(update={"agent_tool_call_budget": 0}),
        expected_action_types=frozenset({"SCHEDULE_INSPECTION"}),
        requires_investigation=False,  # budget is exhausted before it can call the tool
    ),
]
