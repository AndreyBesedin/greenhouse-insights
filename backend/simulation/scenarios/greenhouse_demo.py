from datetime import date

from domain.enums import ManagementPolicyType
from simulation.scenarios.config import ScenarioConfig

# Interview-demo scenario (docs/design/demo_readiness_plan.md section 21,
# Phase 5): a small AGENTIC greenhouse tuned so ordinary simulator dynamics
# - not scripted outcomes - reach watering, an ambiguous/inspection-worthy
# reading, and a harvest within about the first ten simulated days, instead
# of the ~26-40 days gh_001/gh_002 need (see the truss/ripening timing in
# simulation/dynamics/growth.py and ripening.py). A shorter greenhouse also
# means LOWER_PLANT is reachable in that window.
GREENHOUSE_DEMO = ScenarioConfig(
    greenhouse_id="gh_demo",
    name="Agentic Demo Greenhouse",
    description=(
        "Recommended walkthrough greenhouse: 6 cherry tomato plants, 15 days, agentic "
        "management. Tuned to reach watering, inspection and harvest decisions quickly."
    ),
    variety="cherry_tomato",
    rows=2,
    columns=3,
    start_date=date(2026, 1, 1),
    duration_days=15,
    random_seed=4242,
    management_policy=ManagementPolicyType.AGENTIC,
    truss_interval_days=3,
    ripening_days_bounds=(4, 7),
    harvest_ripe_fruit_count_threshold=3,
    lower_plant_height_threshold_cm=35.0,
    lower_plant_amount_cm=15.0,
)
