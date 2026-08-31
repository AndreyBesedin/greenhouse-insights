from pydantic import BaseModel

from domain.enums import FruitStatus, RipenessStage, TrussStage


class Fruit(BaseModel):
    fruit_id: str
    truss_id: str
    plant_id: str
    age_days: int = 0
    diameter_mm: float = 0.0
    mass_g: float = 0.0
    ripeness_stage: RipenessStage = RipenessStage.FRUIT_SET
    status: FruitStatus = FruitStatus.GROWING
    target_diameter_mm: float
    growth_rate_multiplier: float
    ripening_day: int


class Truss(BaseModel):
    truss_id: str
    plant_id: str
    index: int
    age_days: int = 0
    stage: TrussStage = TrussStage.INITIATED
    fruits: list[Fruit] = []


class PlantWorld(BaseModel):
    plant_id: str
    age_days: int = 0
    stem_length_cm: float
    lowered_length_cm: float = 0.0
    water_reservoir_ml: float
    water_stress: float = 0.0
    growth_multiplier: float = 1.0
    trusses: list[Truss] = []
    cumulative_harvest_g: float = 0.0


class GreenhouseEnvironment(BaseModel):
    air_temperature_c: float
    humidity_pct: float


class GreenhouseWorld(BaseModel):
    greenhouse_id: str
    simulated_day: int
    environment: GreenhouseEnvironment
    plants: list[PlantWorld]

    def plant(self, plant_id: str) -> PlantWorld:
        for plant in self.plants:
            if plant.plant_id == plant_id:
                return plant
        raise LookupError(f"no plant {plant_id!r} in greenhouse world {self.greenhouse_id!r}")
