from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant

FORBIDDEN_SIMULATION_FIELDS = {
    "status",
    "current_step",
    "total_steps",
    "scenario_definition",
    "random_seed",
}


def test_plant_constructs_with_required_fields() -> None:
    plant = Plant(plant_id="plant_017", variety="cherry_tomato", row=2, position_in_row=7)

    assert plant.plant_id == "plant_017"
    assert plant.variety == "cherry_tomato"
    assert plant.row == 2
    assert plant.position_in_row == 7


def test_plant_optional_spatial_fields_default_to_none() -> None:
    plant = Plant(plant_id="plant_001", variety="cherry_tomato", row=1, position_in_row=1)

    assert plant.x is None
    assert plant.y is None
    assert plant.zone is None
    assert plant.tray_id is None


def test_plant_accepts_optional_spatial_fields() -> None:
    plant = Plant(
        plant_id="plant_017",
        variety="cherry_tomato",
        row=2,
        position_in_row=7,
        x=6.0,
        y=2.0,
        zone="A1",
        tray_id="tray_04",
    )

    assert plant.x == 6.0
    assert plant.y == 2.0
    assert plant.zone == "A1"
    assert plant.tray_id == "tray_04"


def test_plant_requires_plant_id() -> None:
    with pytest.raises(ValidationError):
        Plant(variety="cherry_tomato", row=1, position_in_row=1)  # type: ignore[call-arg]


def _make_greenhouse(**overrides: object) -> Greenhouse:
    defaults: dict[str, object] = dict(
        greenhouse_id="gh_001",
        name="Simulation Greenhouse 001",
        description="Primary demo greenhouse",
        source_type=SourceType.SIMULATION,
        layout=GreenhouseLayout(rows=4, columns=10),
        plants=[Plant(plant_id="plant_001", variety="cherry_tomato", row=1, position_in_row=1)],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    return Greenhouse(**defaults)


def test_greenhouse_constructs_with_required_fields() -> None:
    greenhouse = _make_greenhouse()

    assert greenhouse.greenhouse_id == "gh_001"
    assert greenhouse.source_type == SourceType.SIMULATION
    assert greenhouse.layout.rows == 4
    assert greenhouse.layout.columns == 10
    assert len(greenhouse.plants) == 1


def test_greenhouse_state_timestamps_default_to_none() -> None:
    greenhouse = _make_greenhouse()

    assert greenhouse.current_state_timestamp is None
    assert greenhouse.latest_available_timestamp is None


def test_greenhouse_model_has_no_simulation_specific_fields() -> None:
    assert set(Greenhouse.model_fields).isdisjoint(FORBIDDEN_SIMULATION_FIELDS)
