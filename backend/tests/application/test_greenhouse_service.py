from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine

from application.auth.models import SERRAPULSE_INTERNAL_ORGANIZATION_ID, Organization
from application.bootstrap import bootstrap_greenhouses
from application.greenhouse_service import (
    CreateGreenhouseRequest,
    GreenhouseService,
    UnknownOrganization,
)
from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.management_trace_repository import ManagementTraceRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.organization_repository import OrganizationRepository
from application.persistence.recommendation_repository import RecommendationRepository
from application.persistence.scenario_config_repository import ScenarioConfigRepository
from application.persistence.simulation_repository import SimulationRepository
from application.persistence.state_repository import StateRepository
from application.persistence.world_repository import WorldRepository
from domain.enums import (
    EventSource,
    EventType,
    ManagementPolicyType,
    ObservationType,
    PlantHealth,
    SimulationStatus,
    SourceType,
)
from domain.event import Event
from domain.greenhouse import Compartment, Greenhouse, GreenhouseLayout, Plant
from domain.management_trace import ManagementTrace
from domain.observation import Observation
from domain.provenance import RecordSource
from domain.recommendation import Recommendation
from domain.state import GreenhouseState, PlantState
from management.validation.actions import WaterPlantAction
from simulation.world_builder import initialize_world
from tests.application.support import ROOT


def test_list_greenhouses_returns_all_seeded_greenhouses(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    items = service.list_greenhouses()

    assert {item.greenhouse_id for item in items} == {"gh_001", "gh_002", "gh_demo"}


def test_list_greenhouses_reports_plant_count_crop_and_not_started_status(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    items = {item.greenhouse_id: item for item in service.list_greenhouses()}
    gh_001 = items["gh_001"]

    assert gh_001.plant_count == 40
    assert gh_001.crop == "cherry_tomato"
    assert gh_001.source_type == SourceType.SIMULATION
    assert gh_001.status == SimulationStatus.NOT_STARTED
    assert gh_001.current_step == 0
    assert gh_001.total_steps == 28


def test_get_greenhouse_detail_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.get_greenhouse_detail("does_not_exist") is None


def test_get_greenhouse_detail_embeds_full_greenhouse_and_simulation_summary(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    detail = service.get_greenhouse_detail("gh_001")

    assert detail is not None
    assert len(detail.greenhouse.plants) == 40
    assert detail.simulation is not None
    assert detail.simulation.simulation_id == "sim_gh_001"
    assert detail.simulation.status == SimulationStatus.NOT_STARTED
    assert detail.simulation.total_steps == 28


DAY_ONE = datetime(2026, 1, 1, tzinfo=UTC)


def _at(day: int) -> datetime:
    return DAY_ONE + timedelta(days=day - 1)


def _save_state(engine: Engine, greenhouse_id: str, day: int) -> None:
    plant_state = PlantState(
        plant_id=f"{greenhouse_id}_plant_001",
        greenhouse_id=greenhouse_id,
        timestamp=_at(day),
        health=PlantHealth.HEALTHY,
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            timestamp=_at(day),
            plant_states=[plant_state],
        )
    )


def test_get_state_returns_the_latest_snapshot_when_no_instant_given(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)
    service = GreenhouseService(engine, ROOT)

    state = service.get_state("gh_001", at=None)

    assert state is not None
    assert state.timestamp == _at(8)


def test_get_state_returns_the_snapshot_as_of_the_given_instant(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    _save_state(engine, "gh_001", day=8)
    service = GreenhouseService(engine, ROOT)

    assert (state := service.get_state("gh_001", at=_at(5))) is not None
    assert state.timestamp == _at(5)
    # Between two snapshots, the earlier one is what was known at that time.
    assert (state := service.get_state("gh_001", at=_at(6))) is not None
    assert state.timestamp == _at(5)


def test_get_state_returns_none_when_no_snapshot_exists_yet(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    assert service.get_state("gh_001", at=_at(3)) is None


def test_get_plant_detail_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.get_plant_detail("does_not_exist", "plant_001", at=None) is None


def test_get_plant_detail_returns_none_for_unknown_plant(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    assert service.get_plant_detail("gh_001", "does_not_exist", at=None) is None


def test_get_plant_detail_returns_plant_config_with_no_state_before_simulation_starts(
    engine: Engine,
) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    detail = service.get_plant_detail("gh_001", "gh_001_plant_001", at=None)

    assert detail is not None
    assert detail.plant.plant_id == "gh_001_plant_001"
    assert detail.state is None


def test_get_plant_detail_includes_that_plants_state_once_it_exists(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    _save_state(engine, "gh_001", day=5)
    service = GreenhouseService(engine, ROOT)

    detail = service.get_plant_detail("gh_001", "gh_001_plant_001", at=_at(5))

    assert detail is not None
    assert detail.state is not None
    assert detail.state.timestamp == _at(5)
    assert detail.state.health == PlantHealth.HEALTHY


def test_get_plant_history_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.get_plant_history("does_not_exist", "plant_001", up_to=_at(10)) is None


def test_get_plant_history_returns_none_for_unknown_plant(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    assert service.get_plant_history("gh_001", "does_not_exist", up_to=_at(10)) is None


def test_get_plant_history_never_returns_states_after_up_to(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    for day in range(1, 6):
        _save_state(engine, "gh_001", day)
    service = GreenhouseService(engine, ROOT)

    history = service.get_plant_history("gh_001", "gh_001_plant_001", up_to=_at(3))

    assert history is not None
    assert [s.timestamp for s in history] == [_at(1), _at(2), _at(3)]


def test_get_plant_history_is_empty_before_any_state_exists(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    history = service.get_plant_history("gh_001", "gh_001_plant_001", up_to=_at(10))

    assert history == []


def test_get_timeline_returns_none_for_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.get_timeline("does_not_exist") is None


def test_get_timeline_is_empty_before_any_snapshot_exists(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)

    timeline = service.get_timeline("gh_001")

    assert timeline is not None
    assert timeline.checkpoints == []
    assert timeline.current_timestamp is None


def test_get_timeline_lists_every_snapshot_instant_in_order(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    for day in (2, 1, 3):
        _save_state(engine, "gh_001", day)
    service = GreenhouseService(engine, ROOT)

    timeline = service.get_timeline("gh_001")

    assert timeline is not None
    assert timeline.checkpoints == [_at(1), _at(2), _at(3)]


def test_create_greenhouse_with_simulation_source_creates_a_runnable_simulation(
    engine: Engine,
) -> None:
    service = GreenhouseService(engine, ROOT)

    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Test Greenhouse",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=2,
            columns=3,
            duration_days=10,
        )
    )

    assert len(detail.greenhouse.plants) == 6
    assert detail.simulation is not None
    assert detail.simulation.status == SimulationStatus.NOT_STARTED
    assert detail.simulation.total_steps == 10

    # It's a real, listable, gettable, runnable greenhouse.
    listed = {item.greenhouse_id: item for item in service.list_greenhouses()}
    assert listed[detail.greenhouse.greenhouse_id].total_steps == 10
    assert service.get_greenhouse_detail(detail.greenhouse.greenhouse_id) is not None


def test_create_greenhouse_without_duration_days_is_rejected_for_simulation_source(
    engine: Engine,
) -> None:
    service = GreenhouseService(engine, ROOT)

    with pytest.raises(ValidationError):
        CreateGreenhouseRequest(
            name="Test Greenhouse",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=1,
            columns=1,
        )
    assert service.list_greenhouses() == []


def test_create_greenhouse_rejects_an_overlong_agentic_duration(engine: Engine) -> None:
    with pytest.raises(ValidationError, match="duration_days"):
        CreateGreenhouseRequest(
            name="Test Greenhouse",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=1,
            columns=1,
            duration_days=31,
            management_policy=ManagementPolicyType.AGENTIC,
        )


def test_create_greenhouse_rejects_too_many_plants_for_agentic(engine: Engine) -> None:
    with pytest.raises(ValidationError, match="rows \\* columns"):
        CreateGreenhouseRequest(
            name="Test Greenhouse",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=5,
            columns=6,
            duration_days=10,
            management_policy=ManagementPolicyType.AGENTIC,
        )


def test_create_greenhouse_allows_the_same_duration_and_size_for_deterministic(
    engine: Engine,
) -> None:
    service = GreenhouseService(engine, ROOT)

    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Big Deterministic Greenhouse",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=5,
            columns=6,
            duration_days=31,
            management_policy=ManagementPolicyType.DETERMINISTIC,
        )
    )

    assert len(detail.greenhouse.plants) == 30


def test_create_greenhouse_with_real_sensors_source_has_no_simulation(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Live Greenhouse",
            source_type=SourceType.REAL_SENSORS,
            crop="cherry_tomato",
            rows=1,
            columns=1,
        )
    )

    assert detail.simulation is None
    listed = {item.greenhouse_id: item for item in service.list_greenhouses()}
    item = listed[detail.greenhouse.greenhouse_id]
    assert item.status is None
    assert item.current_step is None
    assert item.total_steps is None
    timeline = service.get_timeline(detail.greenhouse.greenhouse_id)
    assert timeline is not None
    assert timeline.checkpoints == []


def test_delete_greenhouse_returns_false_for_an_unknown_greenhouse(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    assert service.delete_greenhouse("does_not_exist") is False


def test_delete_greenhouse_removes_a_greenhouse_with_no_simulation(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)
    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Live Greenhouse",
            source_type=SourceType.REAL_SENSORS,
            crop="cherry_tomato",
            rows=1,
            columns=1,
        )
    )
    greenhouse_id = detail.greenhouse.greenhouse_id

    assert service.delete_greenhouse(greenhouse_id) is True

    assert service.get_greenhouse_detail(greenhouse_id) is None
    assert greenhouse_id not in {item.greenhouse_id for item in service.list_greenhouses()}


def test_delete_greenhouse_cleans_up_every_derived_table(engine: Engine) -> None:
    bootstrap_greenhouses(engine)
    service = GreenhouseService(engine, ROOT)
    greenhouse_id = "gh_001"
    simulation_id = "sim_gh_001"
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    ObservationRepository(engine).save_many(
        [
            Observation(
                observation_id="obs_1",
                greenhouse_id=greenhouse_id,
                plant_id="gh_001_plant_001",
                timestamp=timestamp,
                observation_type=ObservationType.SOIL_MOISTURE_PCT,
                value=40.0,
                source=RecordSource(type=SourceType.SIMULATION, source_id=simulation_id),
            )
        ]
    )
    EventRepository(engine).save_many(
        [
            Event(
                event_id="evt_1",
                greenhouse_id=greenhouse_id,
                plant_id="gh_001_plant_001",
                timestamp=timestamp,
                event_type=EventType.WATERING,
                source=EventSource.RULE_BASED_POLICY,
            )
        ]
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            timestamp=timestamp,
            plant_states=[
                PlantState(
                    plant_id="gh_001_plant_001",
                    greenhouse_id=greenhouse_id,
                    timestamp=timestamp,
                    health=PlantHealth.HEALTHY,
                )
            ],
        )
    )
    config = ScenarioConfigRepository(engine).get(greenhouse_id)
    assert config is not None
    WorldRepository(engine).save(initialize_world(config, ["gh_001_plant_001"]))
    ManagementTraceRepository(engine).save(
        ManagementTrace(
            simulation_id=simulation_id,
            greenhouse_id=greenhouse_id,
            simulated_day=1,
            provider="fake",
            model="scripted-v1",
            started_at=timestamp,
            completed_at=timestamp,
        )
    )
    RecommendationRepository(engine).save(
        Recommendation(
            recommendation_id="rec_1",
            source=RecordSource(type=SourceType.SIMULATION, source_id=simulation_id),
            greenhouse_id=greenhouse_id,
            context_timestamp=timestamp,
            plant_id="gh_001_plant_001",
            action=WaterPlantAction(plant_id="gh_001_plant_001", amount_ml=700),
            source_policy=ManagementPolicyType.DETERMINISTIC,
            reason="Soil moisture low.",
            requested_at=timestamp,
        )
    )

    assert service.delete_greenhouse(greenhouse_id) is True

    assert service.get_greenhouse_detail(greenhouse_id) is None
    assert greenhouse_id not in {item.greenhouse_id for item in service.list_greenhouses()}
    assert SimulationRepository(engine).get(simulation_id) is None
    assert ScenarioConfigRepository(engine).get(greenhouse_id) is None
    assert WorldRepository(engine).get_latest(greenhouse_id) is None
    assert StateRepository(engine).get_latest(greenhouse_id) is None
    assert EventRepository(engine).list_for_greenhouse(greenhouse_id) == []
    assert ObservationRepository(engine).list_for_greenhouse(greenhouse_id) == []
    assert ManagementTraceRepository(engine).list_for_simulation(simulation_id) == []
    assert RecommendationRepository(engine).list_for_context(greenhouse_id, timestamp) == []

    # The other bootstrapped greenhouse is untouched.
    assert service.get_greenhouse_detail("gh_002") is not None


def test_list_greenhouses_reports_the_crop_of_a_compartment_without_plants(
    engine: Engine,
) -> None:
    GreenhouseRepository(engine).save(
        Greenhouse(
            greenhouse_id="wur_c306",
            organization_id=SERRAPULSE_INTERNAL_ORGANIZATION_ID,
            name="Compartment 3.06",
            description="Recorded WUR compartment",
            source_type=SourceType.IMPORTED_DATA,
            crop="dwarf_tomato",
            layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
            plants=[],
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    [item] = GreenhouseService(engine, ROOT).list_greenhouses()

    assert item.crop == "dwarf_tomato"
    assert item.plant_count == 0
    assert item.compartment_count == 0
    assert item.status is None


def test_list_greenhouses_counts_compartments_and_the_plants_inside_them(
    engine: Engine,
) -> None:
    GreenhouseRepository(engine).save(
        Greenhouse(
            greenhouse_id="wur_agc4_2024",
            organization_id=SERRAPULSE_INTERNAL_ORGANIZATION_ID,
            name="WUR AGC4 2024",
            description="Six recorded compartments",
            source_type=SourceType.IMPORTED_DATA,
            layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
            plants=[],
            compartments=[
                Compartment(
                    compartment_id="3.06",
                    name="Reference",
                    plants=[
                        Plant(plant_id="306-1", variety="dwarf_tomato", row=1, position_in_row=1)
                    ],
                ),
                Compartment(compartment_id="3.08", name="Trigger"),
            ],
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    [item] = GreenhouseService(engine, ROOT).list_greenhouses()

    assert item.compartment_count == 2
    assert item.plant_count == 1
    # no explicit crop: falls back to the variety of the first plant found
    assert item.crop == "dwarf_tomato"


def test_plant_detail_and_history_find_plants_inside_compartments(engine: Engine) -> None:
    plant = Plant(
        plant_id="wur23_p41", variety="cherry", row=9, position_in_row=1, zone="high light / EC6"
    )
    GreenhouseRepository(engine).save(
        Greenhouse(
            greenhouse_id="wur_agc4_2023",
            organization_id=SERRAPULSE_INTERNAL_ORGANIZATION_ID,
            name="WUR AGC4 2023 pre-trial",
            description="Recorded pre-trial",
            source_type=SourceType.IMPORTED_DATA,
            layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
            plants=[],
            compartments=[
                Compartment(compartment_id="pretrial", name="Pre-trial compartment", plants=[plant])
            ],
            created_at=datetime(2023, 9, 5, tzinfo=UTC),
        )
    )
    at = datetime(2023, 10, 18, 22, tzinfo=UTC)
    state = PlantState(
        plant_id="wur23_p41",
        greenhouse_id="wur_agc4_2023",
        compartment_id="pretrial",
        timestamp=at,
        health=PlantHealth.UNKNOWN,
        latest_plant_height_cm=30.0,
        last_measured_at=datetime(2023, 10, 18, 10, tzinfo=UTC),
    )
    StateRepository(engine).save(
        GreenhouseState.aggregate(greenhouse_id="wur_agc4_2023", timestamp=at, plant_states=[state])
    )
    service = GreenhouseService(engine, ROOT)

    detail = service.get_plant_detail("wur_agc4_2023", "wur23_p41", at=None)

    assert detail is not None
    assert detail.plant == plant
    assert detail.state == state
    assert service.get_plant_history("wur_agc4_2023", "wur23_p41", up_to=at) == [state]
    assert service.get_plant_detail("wur_agc4_2023", "wur23_p99", at=None) is None


def test_create_greenhouse_records_the_owning_organization(engine: Engine) -> None:
    OrganizationRepository(engine).save(
        Organization(
            organization_id="org_acme",
            name="Acme Growers",
            slug="acme",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    service = GreenhouseService(engine, ROOT)

    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Acme north wing",
            organization_id="org_acme",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=1,
            columns=1,
            duration_days=3,
        )
    )

    stored = GreenhouseRepository(engine).get(detail.greenhouse.greenhouse_id)
    assert stored is not None
    assert stored.organization_id == "org_acme"


def test_create_greenhouse_defaults_to_the_internal_organization(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    detail = service.create_greenhouse(
        CreateGreenhouseRequest(
            name="Demo",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=1,
            columns=1,
            duration_days=3,
        )
    )

    assert detail.greenhouse.organization_id == SERRAPULSE_INTERNAL_ORGANIZATION_ID


def test_create_greenhouse_rejects_an_unknown_organization(engine: Engine) -> None:
    service = GreenhouseService(engine, ROOT)

    with pytest.raises(UnknownOrganization):
        service.create_greenhouse(
            CreateGreenhouseRequest(
                name="Orphan",
                organization_id="org_nope",
                source_type=SourceType.SIMULATION,
                crop="cherry_tomato",
                rows=1,
                columns=1,
                duration_days=3,
            )
        )
    assert all(gh.name != "Orphan" for gh in GreenhouseRepository(engine).list())
