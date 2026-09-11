import asyncio

from sqlalchemy import Engine

from application.bootstrap import bootstrap_greenhouses
from application.persistence.event_repository import EventRepository
from application.persistence.simulation_repository import SimulationRepository
from domain.enums import EventType
from simulation.runner import SimulationRunner
from simulation.scenarios import SCENARIO_REGISTRY

CONFIG = SCENARIO_REGISTRY["gh_demo"]

# docs/archive/design-history/demo_readiness_plan.md section 21 (Phase 5): this scenario is
# tuned so ordinary simulator dynamics reach every action type within the
# first ~9 of its 15 days, instead of the ~26-40 days gh_001/gh_002 need -
# this test pins that story so future changes to growth/ripening defaults or
# to this config cannot silently regress it back into a slow demo.
_LATEST_ACCEPTABLE_DAY = {
    EventType.WATERING: 3,
    EventType.MANUAL_INSPECTION: 2,
    EventType.LOWERING: 10,
    EventType.HARVEST: 12,
}


def test_gh_demo_reaches_every_action_type_within_the_scenario(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    runner = SimulationRunner(engine, step_delay_seconds=0)

    asyncio.run(runner.run_to_completion(f"sim_{CONFIG.greenhouse_id}"))

    definition = SimulationRepository(engine).get(f"sim_{CONFIG.greenhouse_id}")
    assert definition is not None
    events = EventRepository(engine).list_for_greenhouse(CONFIG.greenhouse_id)
    first_day_by_type: dict[EventType, int] = {}
    for event in events:
        first_day_by_type.setdefault(
            event.event_type, definition.step_for_timestamp(event.timestamp)
        )

    missing = set(_LATEST_ACCEPTABLE_DAY) - set(first_day_by_type)
    assert not missing, f"expected every action type at least once, missing: {missing}"

    too_late = {
        event_type: first_day_by_type[event_type]
        for event_type, deadline in _LATEST_ACCEPTABLE_DAY.items()
        if first_day_by_type[event_type] > deadline
    }
    assert not too_late, f"action type(s) arrived later than expected: {too_late}"
