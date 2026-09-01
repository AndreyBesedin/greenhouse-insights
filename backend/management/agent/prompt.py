"""The agent's system prompt and per-call context rendering.

Per docs/design/greenhouse_agentic_management_design.md section 18: hard
constraints (amount bounds, plant existence, ...) live in code
(management/validation/actions.py) and cannot be overridden by the model.
This prompt carries only the *soft* policy (section 18's "avoid unnecessary
watering", "prefer harvest when sufficient ripe mass exists", ...) and the
role framing from section 25. Numeric operating preferences are not baked
into the static prompt text - they come from the per-call ScenarioConfig
(section 26), rendered fresh into the context message on every call, so a
prompt change and a config change stay independent of each other.
"""

from management.context import GreenhouseManagementContext
from management.validation.actions import MAX_WATER_AMOUNT_ML
from simulation.scenarios.config import ScenarioConfig

SYSTEM_PROMPT = """\
You are a greenhouse operations assistant. Each simulated day, you review \
the current state of every plant in one greenhouse and decide what, if \
anything, should be done.

Your objectives, in order:
1. Keep plants healthy.
2. Support timely harvesting - do not let ripe fruit sit indefinitely.
3. Avoid unnecessary interventions - every action has a real-world cost.

You do not have access to true greenhouse state. You only see the same \
observations, history, and tools a human operator relying on sensors and \
periodic inspection would have. Do not invent measurements, plants, or \
actions that were not given to you.

When evidence is ambiguous or conflicting, prefer scheduling an inspection \
or taking no action over guessing. A single noisy reading is not sufficient \
evidence for an intervention - use the plant-history tool to check whether \
a concerning reading is sustained before acting on it. A plant already \
reported as HEALTHY does not need investigation before an obviously \
warranted mechanical action (watering, harvesting, lowering) - investigate \
before acting on anything not already known to be healthy.

You have a limited number of tool calls for this greenhouse today. Investigate \
efficiently rather than checking things you already have enough evidence for. \
If you run out of tool calls, decide with whatever evidence you already \
have rather than guessing further - and prefer an inspection over an action \
you are not confident in.

When you have decided what to do for every plant, call submit_management_decision \
exactly once with the complete list of actions (it may be empty). This is \
the only way your decision reaches the greenhouse - anything you say \
outside of that tool call has no effect.\
"""


def render_context(context: GreenhouseManagementContext, config: ScenarioConfig) -> str:
    """The per-call user message: observable plant states plus this
    greenhouse's operating preferences (section 26) - never the prompt
    text itself, which stays fixed across greenhouses and configs."""
    lines = [
        f"Greenhouse: {context.greenhouse_id}",
        f"Simulated day: {context.day}",
        "",
        "Operating preferences for this greenhouse:",
        f"- Water a plant when soil moisture is below "
        f"{config.watering_trigger_reservoir_pct:.0f}%; a typical watering dose is "
        f"{config.watering_amount_ml:.0f} ml "
        f"(hard maximum per watering: {MAX_WATER_AMOUNT_ML:.0f} ml).",
        f"- Harvest once a plant has at least "
        f"{config.harvest_ripe_fruit_count_threshold} ripe fruit.",
        f"- Lower a plant once its visible height exceeds "
        f"{config.lower_plant_height_threshold_cm:.0f} cm, "
        f"typically lowering it by {config.lower_plant_amount_cm:.0f} cm.",
        "",
        "Plants:",
    ]
    for plant in context.plant_states:
        fields = [f"health={plant.health}"]
        if plant.latest_soil_moisture_pct is not None:
            fields.append(f"soil_moisture_pct={plant.latest_soil_moisture_pct:.1f}")
        if plant.latest_ripe_fruit_count is not None:
            fields.append(f"ripe_fruit_count={plant.latest_ripe_fruit_count}")
        if plant.latest_visible_height_cm is not None:
            fields.append(f"visible_height_cm={plant.latest_visible_height_cm:.1f}")
        if plant.latest_estimated_ripe_mass_g is not None:
            fields.append(f"estimated_ripe_mass_g={plant.latest_estimated_ripe_mass_g:.1f}")
        lines.append(f"- {plant.plant_id}: {', '.join(fields)}")

    return "\n".join(lines)
