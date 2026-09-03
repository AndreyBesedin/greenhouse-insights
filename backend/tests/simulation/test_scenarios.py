from domain.enums import ManagementPolicyType
from simulation.scenarios import SCENARIO_REGISTRY


def test_registry_contains_exactly_the_three_poc_greenhouses() -> None:
    assert set(SCENARIO_REGISTRY) == {"gh_001", "gh_002", "gh_demo"}


def test_greenhouse_001_is_the_forty_plant_primary_scenario() -> None:
    config = SCENARIO_REGISTRY["gh_001"]

    assert config.greenhouse_id == "gh_001"
    assert config.rows * config.columns == 40
    assert config.rows == 4
    assert config.columns == 10
    assert config.duration_days == 28


def test_greenhouse_002_is_the_single_plant_longitudinal_scenario() -> None:
    config = SCENARIO_REGISTRY["gh_002"]

    assert config.greenhouse_id == "gh_002"
    assert config.rows * config.columns == 1
    assert config.duration_days == 40


def test_greenhouse_demo_is_the_agentic_walkthrough_scenario() -> None:
    config = SCENARIO_REGISTRY["gh_demo"]

    assert config.greenhouse_id == "gh_demo"
    assert config.management_policy == ManagementPolicyType.AGENTIC
    assert config.duration_days <= 15


def test_scenario_configs_have_distinct_random_seeds() -> None:
    seeds = {config.random_seed for config in SCENARIO_REGISTRY.values()}

    assert len(seeds) == len(SCENARIO_REGISTRY)
