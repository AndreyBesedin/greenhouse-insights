from simulation.actions import HarvestPlantAction, WaterPlantAction
from simulation.policy import DeterministicPolicy, NoOpPolicy
from simulation.scenarios import SCENARIO_REGISTRY
from simulation.world_builder import advance_world, initialize_world

CONFIG = SCENARIO_REGISTRY["gh_001"]
PLANT_ID = "gh_001_plant_001"


def test_no_op_policy_never_requests_actions() -> None:
    world = initialize_world(CONFIG, [PLANT_ID])

    assert NoOpPolicy().decide(world, CONFIG) == []


def test_deterministic_policy_waters_a_plant_with_a_low_reservoir() -> None:
    world = initialize_world(CONFIG, [PLANT_ID])
    thirsty_plant = world.plant(PLANT_ID).model_copy(update={"water_reservoir_ml": 0.0})
    world = world.model_copy(update={"plants": [thirsty_plant]})

    actions = DeterministicPolicy().decide(world, CONFIG)

    assert any(isinstance(a, WaterPlantAction) and a.plant_id == PLANT_ID for a in actions)


def test_deterministic_policy_does_not_water_a_full_reservoir() -> None:
    world = initialize_world(CONFIG, [PLANT_ID])

    actions = DeterministicPolicy().decide(world, CONFIG)

    assert not any(isinstance(a, WaterPlantAction) for a in actions)


def test_deterministic_policy_harvests_once_enough_fruit_is_ripe() -> None:
    world = initialize_world(CONFIG, [PLANT_ID])
    for day in range(1, 61):
        world = advance_world(world, CONFIG, day)

    actions = DeterministicPolicy().decide(world, CONFIG)

    assert any(isinstance(a, HarvestPlantAction) and a.plant_id == PLANT_ID for a in actions)
