from simulation.scenarios.config import ScenarioConfig
from simulation.scenarios.greenhouse_001 import GREENHOUSE_001
from simulation.scenarios.greenhouse_002 import GREENHOUSE_002

SCENARIO_REGISTRY: dict[str, ScenarioConfig] = {
    GREENHOUSE_001.greenhouse_id: GREENHOUSE_001,
    GREENHOUSE_002.greenhouse_id: GREENHOUSE_002,
}

__all__ = ["ScenarioConfig", "SCENARIO_REGISTRY"]
