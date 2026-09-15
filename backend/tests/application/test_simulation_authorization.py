"""Tenant isolation as enforced by SimulationService itself: the same
rules whoever calls, with no HTTP in the loop."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from application.auth.actor import ActorContext
from application.auth.authorizer import Forbidden
from application.auth.models import OrganizationRole
from application.greenhouse_service import CreateGreenhouseRequest, GreenhouseService
from application.simulation_service import SimulationService
from domain.enums import SimulationStatus, SourceType
from management.validation.actions import WaterPlantAction
from tests.application.support import ROOT, member, organization

DAY_ONE = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Scene:
    service: SimulationService
    greenhouse_id: str
    simulation_id: str
    plant_id: str
    viewer_a: ActorContext
    editor_a: ActorContext
    admin_b: ActorContext


@pytest.fixture
def scene(engine: Engine) -> Scene:
    """A one-plant simulation greenhouse in org_a, created the way a
    platform admin would; admin_b runs a different tenant."""
    organization(engine, "org_a")
    organization(engine, "org_b")
    detail = GreenhouseService(engine, ROOT).create_greenhouse(
        CreateGreenhouseRequest(
            name="A",
            organization_id="org_a",
            source_type=SourceType.SIMULATION,
            crop="cherry_tomato",
            rows=1,
            columns=1,
            duration_days=3,
            random_seed=1,
        )
    )
    assert detail.simulation is not None
    return Scene(
        service=SimulationService(engine, step_delay_seconds=0),
        greenhouse_id=detail.greenhouse.greenhouse_id,
        simulation_id=detail.simulation.simulation_id,
        plant_id=detail.greenhouse.plants[0].plant_id,
        viewer_a=member(engine, "viewer-a", "org_a", OrganizationRole.VIEWER),
        editor_a=member(engine, "editor-a", "org_a", OrganizationRole.EDITOR),
        admin_b=member(engine, "admin-b", "org_b", OrganizationRole.ORGANIZATION_ADMIN),
    )


def test_another_tenant_cannot_see_the_simulation(scene: Scene) -> None:
    service, outsider = scene.service, scene.admin_b

    assert service.get_status(outsider, scene.simulation_id) is None
    assert service.get_management_progress(outsider, scene.simulation_id) is None
    assert asyncio.run(service.start_simulation(outsider, scene.simulation_id)) is None
    assert asyncio.run(service.advance_one_day(outsider, scene.simulation_id)) is None
    with pytest.raises(LookupError):
        service.list_recommendations(outsider, scene.greenhouse_id, DAY_ONE)
    with pytest.raises(LookupError):
        asyncio.run(service.approve_all_pending(outsider, scene.greenhouse_id, DAY_ONE))
    with pytest.raises(LookupError):
        asyncio.run(
            service.submit_manual_action(
                outsider,
                scene.greenhouse_id,
                WaterPlantAction(plant_id=scene.plant_id, amount_ml=100),
            )
        )
    assert not service.is_running(scene.simulation_id)


def test_a_viewer_can_read_but_not_steer(scene: Scene) -> None:
    service, viewer = scene.service, scene.viewer_a

    status = service.get_status(viewer, scene.simulation_id)
    assert status is not None and status.status == SimulationStatus.NOT_STARTED
    assert service.list_recommendations(viewer, scene.greenhouse_id, DAY_ONE) == []

    with pytest.raises(Forbidden):
        asyncio.run(service.advance_one_day(viewer, scene.simulation_id))
    with pytest.raises(Forbidden):
        asyncio.run(service.start_simulation(viewer, scene.simulation_id))
    with pytest.raises(Forbidden):
        asyncio.run(service.approve_all_pending(viewer, scene.greenhouse_id, DAY_ONE))
    with pytest.raises(Forbidden):
        asyncio.run(
            service.submit_manual_action(
                viewer,
                scene.greenhouse_id,
                WaterPlantAction(plant_id=scene.plant_id, amount_ml=100),
            )
        )
    assert not service.is_running(scene.simulation_id)


def test_an_editor_can_advance_their_own_simulation(scene: Scene) -> None:
    definition = asyncio.run(scene.service.advance_one_day(scene.editor_a, scene.simulation_id))

    assert definition is not None
    assert definition.current_step == 1


def test_reviewing_another_tenants_recommendation_is_absent_not_forbidden(scene: Scene) -> None:
    service = scene.service
    # Day 1 proposes nothing for this seed; day 2 proposes watering.
    asyncio.run(service.advance_one_day(ROOT, scene.simulation_id))
    definition = asyncio.run(service.advance_one_day(ROOT, scene.simulation_id))
    assert definition is not None
    pending = service.list_recommendations(
        ROOT, scene.greenhouse_id, definition.timestamp_for_step(2)
    )
    assert pending, "the deterministic policy should propose something by day two"

    for recommendation in pending:
        rec_id = recommendation.recommendation_id
        assert asyncio.run(service.approve_recommendation(scene.admin_b, rec_id)) is None
        assert asyncio.run(service.dismiss_recommendation(scene.admin_b, rec_id)) is None
        with pytest.raises(Forbidden):
            asyncio.run(service.dismiss_recommendation(scene.viewer_a, rec_id))
    assert all(
        r.status == recommendation.status
        for r, recommendation in zip(
            service.list_recommendations(
                ROOT, scene.greenhouse_id, definition.timestamp_for_step(2)
            ),
            pending,
            strict=True,
        )
    )
