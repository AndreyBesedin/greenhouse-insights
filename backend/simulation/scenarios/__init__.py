from simulation.scenarios.config import ScenarioConfig
from simulation.scenarios.greenhouse_001 import GREENHOUSE_001
from simulation.scenarios.greenhouse_002 import GREENHOUSE_002
from simulation.scenarios.greenhouse_demo import GREENHOUSE_DEMO

SCENARIO_REGISTRY: dict[str, ScenarioConfig] = {
    GREENHOUSE_001.greenhouse_id: GREENHOUSE_001,
    GREENHOUSE_002.greenhouse_id: GREENHOUSE_002,
    GREENHOUSE_DEMO.greenhouse_id: GREENHOUSE_DEMO,
}

__all__ = ["ScenarioConfig", "SCENARIO_REGISTRY"]
