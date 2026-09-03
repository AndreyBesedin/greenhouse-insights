"""Turns a policy's bare RequestedAction into a persisted, human-facing
Recommendation - docs/design/demo_readiness_plan.md section 11: "The
management-policy contract can still return requested actions internally,
but the application layer must persist them as pending recommendations
before execution." This is that application-layer step; management/ never
sees or produces a Recommendation.

reason/evidence are generated here from the same observable PlantState the
policy itself saw (never simulator-hidden truth), using plain per-action-
type templates rather than asking the policy/agent to explain itself - the
UI must show concise structured facts, not chain-of-thought (section 4).
"""

from datetime import datetime

from domain.recommendation import Recommendation
from domain.state import PlantState
from management.validation.actions import (
    HarvestPlantAction,
    LowerPlantAction,
    RequestedAction,
    ScheduleInspectionAction,
    WaterPlantAction,
)
from simulation.runner import DayProposal

Evidence = dict[str, float | int | str | None]


def build_recommendation(
    proposal: DayProposal,
    action: RequestedAction,
    *,
    recommendation_id: str,
    requested_at: datetime,
) -> Recommendation:
    plant_state = proposal.plant_states_by_id.get(action.plant_id)
    reason: str
    evidence: Evidence
    if plant_state is None:
        reason, evidence = "No observable state available for this plant.", {}
    else:
        reason, evidence = _reason_and_evidence(action, plant_state)

    return Recommendation(
        recommendation_id=recommendation_id,
        simulation_id=proposal.simulation_id,
        greenhouse_id=proposal.greenhouse_id,
        simulated_day=proposal.simulated_day,
        plant_id=action.plant_id,
        action=action,
        source_policy=proposal.management_policy,
        reason=reason,
        evidence=evidence,
        requested_at=requested_at,
    )


def _reason_and_evidence(action: RequestedAction, plant_state: PlantState) -> tuple[str, Evidence]:
    if isinstance(action, WaterPlantAction):
        pct = plant_state.latest_soil_moisture_pct
        reason = (
            f"Soil moisture at {pct:.0f}%." if pct is not None else "Soil moisture unavailable."
        )
        return reason, {"soil_moisture_pct": pct}

    if isinstance(action, HarvestPlantAction):
        count = plant_state.latest_ripe_fruit_count
        mass = plant_state.latest_estimated_ripe_mass_g
        mass_clause = f", estimated {mass:.0f} g" if mass is not None else ""
        reason = f"{count if count is not None else 'Several'} ripe fruit ready{mass_clause}."
        return reason, {"ripe_fruit_count": count, "estimated_ripe_mass_g": mass}

    if isinstance(action, LowerPlantAction):
        height = plant_state.latest_visible_height_cm
        reason = (
            f"Visible height at {height:.0f} cm." if height is not None else "Height unavailable."
        )
        return reason, {"visible_height_cm": height}

    assert isinstance(action, ScheduleInspectionAction)
    return action.reason, {"soil_moisture_pct": plant_state.latest_soil_moisture_pct}
