"""Ground-truth eval cases for agent decision quality.

Per docs/archive/design-history/greenhouse_agentic_management_design.md §35-37: each case
pairs an observable context (what any AgentModelProvider is allowed to see)
with a private expected outcome (§36) the provider never sees. Kept small
and provider-agnostic on purpose - these run against FakeAgentModelProvider
today and against a real provider unchanged later.

Per docs/archive/design-history/domain_model_eval_refactor_plan.md PR 3 ("Level A" there):
every case's input is a plausible day's Observations (plus, where needed,
prior days' Observations for history) run through the same
reconstruct_plant_state the application uses - never a hand-set PlantState.
That's what makes a case's PlantState/health combination reachable: it is
whatever the real reconstruction code would produce from that observation
set, not a label chosen to make the assertion easy. Omitting an observation
type is a real gap (e.g. no camera reading that day), not a zero reading -
see assess_plant_condition's docstring for what that gap means for health.
"""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from domain.enums import ObservationType, PlantHealth, SourceType
from domain.event import Event
from domain.observation import Observation
from domain.provenance import RecordSource
from domain.state import PlantState
from intelligence.state_reconstruction import reconstruct_plant_state
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.scenarios.config import ScenarioConfig

CONFIG = SCENARIO_REGISTRY["gh_001"]
_BASE_DATE = datetime(2026, 1, 1, tzinfo=UTC)


def _timestamp_for(day: int) -> datetime:
    return _BASE_DATE + timedelta(days=day - 1)


class EvalCase(BaseModel):
    case_id: str
    description: str
    plant_id: str = "eval_plant"
    greenhouse_id: str = "gh_eval"
    day: int = 20
    observations: list[Observation]
    """This day's observations for plant_id - the smallest realistic set
    for the case. Built with _observations() below."""
    history_observations: list[list[Observation]] = []
    """Prior days' observations for the same plant, oldest first - each
    entry becomes one day the policy's get_plant_history tool can return,
    via reconstruct_plant_state (build_history())."""
    events: list[Event] = []
    config: ScenarioConfig = CONFIG
    expected_action_types: frozenset[str]
    """Exact set of action_type values a correct decision returns. Empty
    means "no action is the right call"."""
    param_ranges: dict[str, tuple[str, float, float]] = {}
    """action_type -> (field_name, min, max) for that action's primary
    numeric parameter, e.g. {"WATER_PLANT": ("amount_ml", 400.0, 900.0)}."""
    requires_investigation: bool
    """Whether a correct decision must call get_plant_history before
    acting - true for anything the current day's evidence alone leaves
    ambiguous (§9)."""
    expected_condition: PlantHealth | None = None
    """Optional: asserts reconstruct_plant_state's health for this case -
    used by the cases that specifically prove the environment/health
    distinction, left unset elsewhere to keep other cases focused."""


def _observations(
    plant_id: str,
    day: int,
    *,
    soil_moisture_pct: float | None = None,
    visible_fruit_count: float | None = None,
    ripe_fruit_count: float | None = None,
    estimated_ripe_mass_g: float | None = None,
    visible_height_cm: float | None = None,
) -> list[Observation]:
    """One plausible day's observations for one plant - only the given
    readings are included, so an omitted kwarg is a real observation gap,
    not a zero reading."""
    timestamp = _timestamp_for(day)
    values: list[tuple[ObservationType, float | None]] = [
        (ObservationType.SOIL_MOISTURE_PCT, soil_moisture_pct),
        (ObservationType.VISIBLE_FRUIT_COUNT, visible_fruit_count),
        (ObservationType.RIPE_FRUIT_COUNT, ripe_fruit_count),
        (ObservationType.ESTIMATED_RIPE_MASS_G, estimated_ripe_mass_g),
        (ObservationType.VISIBLE_HEIGHT_CM, visible_height_cm),
    ]
    return [
        Observation(
            observation_id=f"obs_{plant_id}_d{day}_{observation_type.value}",
            greenhouse_id="gh_eval",
            plant_id=plant_id,
            timestamp=timestamp,
            observation_type=observation_type,
            value=value,
            source=RecordSource(type=SourceType.SIMULATION, source_id="sim_eval"),
        )
        for observation_type, value in values
        if value is not None
    ]


def build_plant_state(case: EvalCase) -> PlantState:
    return reconstruct_plant_state(
        plant_id=case.plant_id,
        greenhouse_id=case.greenhouse_id,
        timestamp=_timestamp_for(case.day),
        observations=case.observations,
        events=case.events,
    )


def build_history(case: EvalCase) -> list[PlantState]:
    start_day = case.day - len(case.history_observations)
    return [
        reconstruct_plant_state(
            plant_id=case.plant_id,
            greenhouse_id=case.greenhouse_id,
            timestamp=_timestamp_for(start_day + offset),
            observations=day_observations,
            events=[],
        )
        for offset, day_observations in enumerate(case.history_observations)
    ]


CASES: list[EvalCase] = [
    EvalCase(
        case_id="sustained_low_moisture_waters_while_staying_healthy",
        description="Low soil moisture confirmed by sustained history should be watered. "
        "A single low reading is ambiguous and must be investigated first regardless of "
        "the plant's own condition, but a sustained one is not - and watering need never "
        "implies poor plant condition (the environment/health distinction).",
        observations=_observations("eval_plant", 20, soil_moisture_pct=10.0, visible_fruit_count=3),
        history_observations=[
            _observations("eval_plant", 19, soil_moisture_pct=9.0, visible_fruit_count=3)
        ],
        expected_action_types=frozenset({"WATER_PLANT"}),
        param_ranges={"WATER_PLANT": ("amount_ml", 400.0, 900.0)},
        requires_investigation=True,
        expected_condition=PlantHealth.HEALTHY,
    ),
    EvalCase(
        case_id="single_low_reading_inspects_not_waters",
        description="A single low-moisture reading with no sustained history is ambiguous "
        "evidence - schedule an inspection, do not water on a single noisy reading. Paired "
        "with the case above: identical current-day evidence, different history, different "
        "outcome (longitudinal evidence changing the decision).",
        observations=_observations("eval_plant", 20, soil_moisture_pct=12.0, visible_fruit_count=3),
        expected_action_types=frozenset({"SCHEDULE_INSPECTION"}),
        requires_investigation=True,
        expected_condition=PlantHealth.HEALTHY,
    ),
    EvalCase(
        case_id="adequate_moisture_no_trigger_does_nothing",
        description="Adequate soil moisture with a full, normal reading set and no other "
        "trigger needs no action.",
        observations=_observations(
            "eval_plant",
            20,
            soil_moisture_pct=85.0,
            visible_fruit_count=3,
            ripe_fruit_count=1,
            estimated_ripe_mass_g=50.0,
            visible_height_cm=100.0,
        ),
        expected_action_types=frozenset(),
        requires_investigation=False,
        expected_condition=PlantHealth.HEALTHY,
    ),
    EvalCase(
        case_id="ripe_fruit_harvests",
        description="Enough ripe fruit should be harvested, unconditionally - no "
        "investigation needed for a mechanical, unambiguous reading.",
        observations=_observations(
            "eval_plant",
            20,
            soil_moisture_pct=85.0,
            visible_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
            ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
            estimated_ripe_mass_g=300.0,
        ),
        expected_action_types=frozenset({"HARVEST_PLANT"}),
        requires_investigation=False,
    ),
    EvalCase(
        case_id="excessive_height_lowers",
        description="A plant taller than the threshold should be lowered.",
        observations=_observations(
            "eval_plant",
            20,
            soil_moisture_pct=85.0,
            visible_fruit_count=3,
            visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 15,
        ),
        expected_action_types=frozenset({"LOWER_PLANT"}),
        param_ranges={"LOWER_PLANT": ("amount_cm", 20.0, 60.0)},
        requires_investigation=False,
    ),
    EvalCase(
        case_id="independent_triggers_all_act",
        description="Independent triggers (sustained low moisture, ripe fruit, excessive "
        "height) firing together should each produce their own recommendation - none "
        "should be missed. Harvest/lower are unambiguous; sustained low moisture still "
        "requires investigation, same as watering alone.",
        observations=_observations(
            "eval_plant",
            20,
            soil_moisture_pct=5.0,
            visible_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
            ripe_fruit_count=CONFIG.harvest_ripe_fruit_count_threshold,
            visible_height_cm=CONFIG.lower_plant_height_threshold_cm + 20,
        ),
        history_observations=[
            _observations("eval_plant", 19, soil_moisture_pct=4.0, visible_fruit_count=3)
        ],
        expected_action_types=frozenset({"WATER_PLANT", "HARVEST_PLANT", "LOWER_PLANT"}),
        param_ranges={
            "WATER_PLANT": ("amount_ml", 400.0, 900.0),
            "LOWER_PLANT": ("amount_cm", 20.0, 60.0),
        },
        requires_investigation=True,
    ),
    EvalCase(
        case_id="condition_concern_with_adequate_moisture_needs_inspection",
        description="Adequate soil moisture but no visible/fruit reading today (e.g. the "
        "vision pipeline is down while the soil sensor still reports) is a genuine "
        "plant-condition concern unrelated to soil moisture - inspection is needed, but "
        "the moisture value itself is not in question and needs no history check.",
        observations=_observations("eval_plant", 20, soil_moisture_pct=75.0),
        expected_action_types=frozenset({"SCHEDULE_INSPECTION"}),
        requires_investigation=False,
        expected_condition=PlantHealth.MONITOR,
    ),
    EvalCase(
        case_id="budget_exhausted_falls_back_to_inspection",
        description="When the tool-call budget is exhausted before an ambiguous "
        "low-moisture reading can be investigated, the safe fallback is inspection - "
        "never guess and water.",
        observations=_observations("eval_plant", 20, soil_moisture_pct=8.0, visible_fruit_count=3),
        config=CONFIG.model_copy(update={"agent_tool_call_budget": 0}),
        expected_action_types=frozenset({"SCHEDULE_INSPECTION"}),
        requires_investigation=False,  # budget is exhausted before it can call the tool
        expected_condition=PlantHealth.HEALTHY,
    ),
]
