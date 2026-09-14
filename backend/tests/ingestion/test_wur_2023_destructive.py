from datetime import UTC, datetime, timedelta
from io import BytesIO

import openpyxl
import pytest

from domain.enums import EventSource, EventType, ObservationType, SourceType
from domain.event import Event
from domain.observation import Observation
from domain.provenance import RecordSource
from ingestion.loader import reconstruct_checkpoints
from ingestion.wur.agc4_pretrial_2023.compartments import COMPARTMENT_ID, GREENHOUSE_ID
from ingestion.wur.agc4_pretrial_2023.destructive import parameter_name, read_destructive_samples
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE

HEADER = [
    "DAS", "Date", "Phase", "Plant density (p/m2)", "Treatment", "Variety", "EC", "Light",
    "Sample name", "Sample n", "Plant height", "n. flower clusters (#/plant)",
    "N. red fruits (#/plant)", "FW Whole plants measured (g/plant)",
    "Leaf Area measured (cm²/plant)", "SLA (cm2/g DW)",
]  # fmt: skip


def _read(*rows: list[object], header: list[str] = HEADER) -> list[Event]:
    book = openpyxl.Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "All Data"
    # the real sheet has blank rows and a sowing-date row above its header
    sheet.append([None])
    sheet.append(["Sowing date", None, datetime(2023, 8, 15)])
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    buffer.seek(0)
    return read_destructive_samples(buffer)


def _nursery(name: str, ec: str, light: str, height: float = 11) -> list[object]:
    """An untreated transplant sample, as `All Data` lists it under one of
    the treatment-coded names it was copied to."""
    return [
        20, datetime(2023, 9, 4), "Transplant", 1050, "No treatment", "Cherry", ec, light,
        name, 1, height, "N/A", None, 1.37, 29.31, 350.0,
    ]  # fmt: skip


END_PRODUCT = [
    86, datetime(2023, 11, 9), "End product", 20, "Cherry_EC6_HighLight", "Cherry", "EC6",
    "high light", "Cherry_EC6_HL_1", 1, 43, 26, 15, 441.9, 2195.0, 127.1,
]  # fmt: skip


def test_each_sample_is_a_compartment_event_at_local_noon() -> None:
    nursery, end_product = _read(_nursery("Cherry_EC3_1", "EC3", "no light"), END_PRODUCT)

    assert nursery.event_type == EventType.DESTRUCTIVE_SAMPLE
    assert nursery.source == EventSource.HUMAN_REPORTED
    assert (nursery.greenhouse_id, nursery.compartment_id, nursery.plant_id) == (
        GREENHOUSE_ID,
        COMPARTMENT_ID,
        None,
    )
    # 4 September is summer time, 9 November winter time
    assert nursery.timestamp == datetime(2023, 9, 4, 10, tzinfo=UTC)
    assert end_product.timestamp == datetime(2023, 11, 9, 11, tzinfo=UTC)
    assert end_product.event_id == "wur23_sample_20231109_Cherry_EC6_HL_1"


def test_treated_samples_carry_identity_and_measurements_but_not_n_a_or_blanks() -> None:
    [end_product] = _read(END_PRODUCT)

    assert end_product.parameters == {
        "sample_name": "Cherry_EC6_HL_1",
        "phase": "End product",
        "treatment": "Cherry_EC6_HighLight",
        "variety": "Cherry",
        "ec": "EC6",
        "light": "high light",
        "days_after_sowing": 86.0,
        "plant_density_per_m2": 20.0,
        "sample_number": 1.0,
        "plant_height": 43.0,
        "n_flower_clusters_count_per_plant": 26.0,
        "n_red_fruits_count_per_plant": 15.0,
        "fw_whole_plants_measured_g_per_plant": 441.9,
        "leaf_area_measured_cm2_per_plant": 2195.0,
        "sla_cm2_per_g_dw": 127.1,
    }


def test_copies_of_one_untreated_sample_become_a_single_event() -> None:
    events = _read(
        _nursery("Cherry_EC6_HL_1", "EC6", "high light"),
        _nursery("Cherry_EC3_1", "EC3", "no light"),
        _nursery("Cherry_EC6_ML_1", "EC6", "med light"),
    )

    [nursery] = events
    assert nursery.event_id == "wur23_sample_20230904_untreated_1"
    assert nursery.parameters == {
        "sample_name": "untreated_1",
        "listed_as": ["Cherry_EC3_1", "Cherry_EC6_HL_1", "Cherry_EC6_ML_1"],
        "phase": "Transplant",
        "treatment": "No treatment",
        "variety": "Cherry",
        "days_after_sowing": 20.0,
        "plant_density_per_m2": 1050.0,
        "sample_number": 1.0,
        "plant_height": 11.0,
        "fw_whole_plants_measured_g_per_plant": 1.37,
        "leaf_area_measured_cm2_per_plant": 29.31,
        "sla_cm2_per_g_dw": 350.0,
    }


def test_untreated_samples_that_disagree_are_not_merged_and_are_refused() -> None:
    # same sample number, different measurements: two plants claiming one name
    with pytest.raises(ValueError, match="repeat on the same date"):
        _read(
            _nursery("Cherry_EC6_HL_1", "EC6", "high light", height=11),
            _nursery("Cherry_EC3_1", "EC3", "no light", height=12),
        )


def test_parameter_names_keep_their_units() -> None:
    assert parameter_name("FW leaves (g/plant)") == "fw_leaves_g_per_plant"
    assert parameter_name("N. fruit set (#/plant)") == "n_fruit_set_count_per_plant"
    assert parameter_name("Leaf area cotyledones (cm²/plant)") == (
        "leaf_area_cotyledones_cm2_per_plant"
    )


def test_unexpected_text_in_a_measurement_is_refused() -> None:
    broken = list(END_PRODUCT)
    broken[HEADER.index("Plant height")] = "tall"

    with pytest.raises(ValueError):
        _read(broken)


def test_a_treated_sample_name_repeated_on_one_date_is_refused() -> None:
    with pytest.raises(ValueError, match="repeat on the same date"):
        _read(END_PRODUCT, END_PRODUCT)


def test_samples_never_count_as_harvested_mass() -> None:
    samples = _read(_nursery("Cherry_EC3_1", "EC3", "no light"), END_PRODUCT)
    climate = Observation(
        observation_id="t_air",
        greenhouse_id=GREENHOUSE_ID,
        compartment_id=COMPARTMENT_ID,
        plant_id=None,
        timestamp=datetime(2023, 11, 9, 12, tzinfo=UTC),
        observation_type=ObservationType.AIR_TEMPERATURE_C,
        value=19.0,
        source=RecordSource(type=SourceType.IMPORTED_DATA, source_id="test"),
    )

    [state] = reconstruct_checkpoints(
        GREENHOUSE_ID, [climate], samples, every=timedelta(days=1), timezone=WUR_LOCAL_TIMEZONE
    )

    assert state.total_harvested_g == 0.0
    compartment = state.compartment(COMPARTMENT_ID)
    assert compartment is not None
    assert compartment.harvested_total_g == 0.0
