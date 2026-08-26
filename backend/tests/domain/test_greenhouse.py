import pytest
from pydantic import ValidationError

from domain.greenhouse import Plant


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
