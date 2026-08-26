from enum import StrEnum


class SourceType(StrEnum):
    SIMULATION = "SIMULATION"
    REAL_SENSORS = "REAL_SENSORS"
    EXTERNAL_API = "EXTERNAL_API"
    IMPORTED_DATA = "IMPORTED_DATA"
