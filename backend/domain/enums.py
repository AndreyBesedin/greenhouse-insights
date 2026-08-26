from enum import StrEnum


class SourceType(StrEnum):
    SIMULATION = "SIMULATION"
    REAL_SENSORS = "REAL_SENSORS"
    EXTERNAL_API = "EXTERNAL_API"
    IMPORTED_DATA = "IMPORTED_DATA"


class ObservationType(StrEnum):
    SOIL_MOISTURE_PCT = "soil_moisture_pct"
    AIR_TEMPERATURE_C = "air_temperature_c"
    VISIBLE_FRUIT_COUNT = "visible_fruit_count"
    RIPE_FRUIT_COUNT = "ripe_fruit_count"
