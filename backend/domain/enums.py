from enum import StrEnum


class SourceType(StrEnum):
    SIMULATION = "SIMULATION"
    REAL_SENSORS = "REAL_SENSORS"
    EXTERNAL_API = "EXTERNAL_API"
    IMPORTED_DATA = "IMPORTED_DATA"


class ObservationType(StrEnum):
    SOIL_MOISTURE_PCT = "soil_moisture_pct"
    AIR_TEMPERATURE_C = "air_temperature_c"
    VISIBLE_FRUIT_COUNT = "visible_fruit_count"
    RIPE_FRUIT_COUNT = "ripe_fruit_count"
    ESTIMATED_RIPE_MASS_G = "estimated_ripe_mass_g"
    VISIBLE_HEIGHT_CM = "visible_height_cm"


class EventType(StrEnum):
    WATERING = "WATERING"
    HARVEST = "HARVEST"
    LOWERING = "LOWERING"
    PRUNING = "PRUNING"
    FERTILISATION = "FERTILISATION"
    MANUAL_INSPECTION = "MANUAL_INSPECTION"


class EventSource(StrEnum):
    HUMAN_REPORTED = "HUMAN_REPORTED"
    ROBOT_CONFIRMED = "ROBOT_CONFIRMED"
    CONTROL_SYSTEM = "CONTROL_SYSTEM"
    INFERRED_FROM_OBSERVATIONS = "INFERRED_FROM_OBSERVATIONS"
    SIMULATION = "SIMULATION"
    RULE_BASED_POLICY = "RULE_BASED_POLICY"
    AGENT = "AGENT"


class FruitStatus(StrEnum):
    GROWING = "GROWING"
    RIPE = "RIPE"
    HARVESTED = "HARVESTED"


class RipenessStage(StrEnum):
    FRUIT_SET = "FRUIT_SET"
    IMMATURE_GREEN = "IMMATURE_GREEN"
    MATURE_GREEN = "MATURE_GREEN"
    TURNING = "TURNING"
    RIPE = "RIPE"
    OVERRIPE = "OVERRIPE"


class TrussStage(StrEnum):
    INITIATED = "INITIATED"
    FRUITING = "FRUITING"
    HARVESTABLE = "HARVESTABLE"
    INACTIVE = "INACTIVE"


class Provenance(StrEnum):
    OBSERVED = "OBSERVED"
    REPORTED = "REPORTED"
    DETERMINISTICALLY_DERIVED = "DETERMINISTICALLY_DERIVED"
    INFERRED = "INFERRED"


class PlantHealth(StrEnum):
    """The plant's own condition, assessed independently of environmental
    readings such as soil moisture (docs/archive/design-history/domain_model_eval_refactor_plan.md
    PR 2) - a plant needing water is not automatically unhealthy. For this
    POC there is one implemented condition signal beyond presence/absence
    of observations: MONITOR when the plant's own visible/fruit readings
    are missing today despite an environment reading coming in (PR 3's
    intelligence.state_reconstruction.assess_plant_condition) - otherwise
    HEALTHY once any observation exists, UNKNOWN before that.
    ACTION_REQUIRED stays available for future condition-specific evidence
    (visual symptoms, sustained deterioration, ...)."""

    HEALTHY = "HEALTHY"
    MONITOR = "MONITOR"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    UNKNOWN = "UNKNOWN"


class SimulationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ManagementPolicyType(StrEnum):
    NONE = "NONE"
    DETERMINISTIC = "DETERMINISTIC"
    AGENTIC = "AGENTIC"


class ActionExecutorType(StrEnum):
    """Who/what actually carries out an accepted action, as opposed to who
    decided it (see management/). Only one member exists today - it makes
    the choice a real, persisted, per-simulation setting rather than a
    hardcoded function call, so a second implementation (a simulated robot
    with different characteristics, later a real one) is a new member plus
    one new class, not a refactor."""

    SIMULATED_OPERATOR = "SIMULATED_OPERATOR"


class RecommendationStatus(StrEnum):
    """Avoid adding statuses with no immediate use
    (docs/archive/design-history/demo_readiness_plan.md section 10):
    approval and execution are synchronous in this pass, so
    there is no persisted APPROVED-but-not-yet-executed state, and nothing
    in the executor can currently fail once validation has passed, so
    there is no FAILED state either."""

    PENDING = "PENDING"
    DISMISSED = "DISMISSED"
    EXECUTED = "EXECUTED"
    REJECTED_BY_VALIDATOR = "REJECTED_BY_VALIDATOR"


class ApprovalSource(StrEnum):
    """Who approved a recommendation - section 7's approved_by. Only one
    member for now (every approval in this pass comes from a human
    operator); a future AUTOMATION_POLICY approver is a new member, not a
    refactor, same pattern as ActionExecutorType."""

    HUMAN = "HUMAN"
