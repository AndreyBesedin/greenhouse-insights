"""Loading a canonical greenhouse into the application database: the
records themselves plus reconstructed GreenhouseState snapshots at regular
checkpoints, so the existing timeline / state endpoints can navigate a
recorded history exactly as they navigate a simulated one.

Checkpoint semantics (docs/design/wur_real_data_ingestion_replay_plan.md
section 11): a snapshot at checkpoint T is reconstructed from every record
with timestamp <= T and nothing later. Its own timestamp is the instant of
the last observation at or before T - the exact underlying time the state
was last known, not a rounded boundary.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from itertools import islice

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.state_repository import StateRepository
from domain.accumulation import DAILY_TOTAL_FIELD, accounting_day
from domain.enums import EventType, ObservationType, PlantHealth
from domain.event import Event
from domain.observation import Observation
from domain.state import (
    CompartmentState,
    GreenhouseEnvironmentState,
    GreenhouseState,
    PlantState,
)
from ingestion.canonical import CanonicalGreenhouse

_BATCH = 5_000

# Plant-level manual measurement types -> the PlantState field holding the
# latest reading. Red fruit (RIPE_FRUIT_COUNT) goes to the integer count field.
_PLANT_FIELD: dict[ObservationType, str] = {
    ObservationType.PLANT_HEIGHT_CM: "latest_plant_height_cm",
    ObservationType.LEAF_COUNT: "latest_leaf_count",
    ObservationType.LEAF_LENGTH_CM: "latest_leaf_length_cm",
    ObservationType.LEAF_WIDTH_CM: "latest_leaf_width_cm",
    ObservationType.TRUSS_COUNT: "latest_truss_count",
    ObservationType.OPEN_FLOWER_COUNT: "latest_open_flower_count",
    ObservationType.GREEN_FRUIT_COUNT: "latest_green_fruit_count",
    ObservationType.COLOURED_FRUIT_COUNT: "latest_coloured_fruit_count",
}


@dataclass(frozen=True)
class TimeWindow:
    """Inclusive bounds on record timestamps; either side may be open."""

    start: datetime | None = None
    end: datetime | None = None

    def contains(self, timestamp: datetime) -> bool:
        if self.start is not None and timestamp < self.start:
            return False
        return self.end is None or timestamp <= self.end


@dataclass(frozen=True)
class LoadReport:
    greenhouse_id: str
    observations: int
    events: int
    snapshots: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None


def load_canonical_greenhouse(
    engine: Engine,
    canonical: CanonicalGreenhouse,
    *,
    window: TimeWindow | None = None,
    compartment_ids: Collection[str] | None = None,
    checkpoint_every: timedelta = timedelta(days=1),
    checkpoint_timezone: tzinfo = UTC,
) -> LoadReport:
    """Replaces whatever the database held for this greenhouse. With
    `compartment_ids`, only records of those compartments (and records
    scoped to the greenhouse as a whole) are loaded."""
    window = window or TimeWindow()

    def selected(compartment_id: str | None) -> bool:
        return (
            compartment_ids is None or compartment_id is None or compartment_id in compartment_ids
        )

    greenhouse = canonical.greenhouse()
    greenhouse_id = greenhouse.greenhouse_id

    observations_repo = ObservationRepository(engine)
    events_repo = EventRepository(engine)
    states_repo = StateRepository(engine)
    observations_repo.delete_for_greenhouse(greenhouse_id)
    events_repo.delete_for_greenhouse(greenhouse_id)
    states_repo.delete_for_greenhouse(greenhouse_id)

    events = [
        e for e in canonical.events() if window.contains(e.timestamp) and selected(e.compartment_id)
    ]
    events_repo.save_many(events)

    snapshots = 0
    observation_count = 0
    first: datetime | None = None
    last: datetime | None = None

    def persisted(source: Iterable[Observation]) -> Iterator[Observation]:
        nonlocal observation_count, first, last
        for batch in _batched(source, _BATCH):
            observations_repo.save_many(batch)
            observation_count += len(batch)
            first = first or batch[0].timestamp
            last = batch[-1].timestamp
            yield from batch

    in_window = (
        o
        for o in canonical.observations()
        if window.contains(o.timestamp) and selected(o.compartment_id)
    )
    plant_compartments: dict[str, str | None] = {
        plant.plant_id: None for plant in greenhouse.plants
    }
    for compartment in greenhouse.compartments:
        if selected(compartment.compartment_id):
            plant_compartments.update(
                {plant.plant_id: compartment.compartment_id for plant in compartment.plants}
            )

    for state in reconstruct_checkpoints(
        greenhouse_id,
        persisted(in_window),
        events,
        every=checkpoint_every,
        timezone=checkpoint_timezone,
        plant_compartments=plant_compartments,
    ):
        states_repo.save(state)
        snapshots += 1

    GreenhouseRepository(engine).save(
        greenhouse.model_copy(
            update={"current_state_timestamp": last, "latest_available_timestamp": last}
        )
    )
    return LoadReport(greenhouse_id, observation_count, len(events), snapshots, first, last)


def reconstruct_checkpoints(
    greenhouse_id: str,
    observations: Iterable[Observation],
    events: list[Event],
    *,
    every: timedelta,
    timezone: tzinfo,
    plant_compartments: Mapping[str, str | None] | None = None,
) -> Iterator[GreenhouseState]:
    """Walks chronologically ordered observations once, emitting a state at
    the last observation before each checkpoint boundary and at the end.
    Boundaries are aligned to local midnight in `timezone` for daily
    cadences (so a checkpoint is "end of that day" where the greenhouse
    stands), and to `every` multiples within the day otherwise.

    With `plant_compartments` (plant id -> its compartment), every snapshot
    carries a PlantState per plant, in plant-id order, holding its latest
    readings so far; a plant not yet measured has none. Health stays UNKNOWN:
    weekly manual measurements carry no evidence of the plant's condition."""
    # Latest value of each type, per scope: None is the greenhouse as a
    # whole, any other key a compartment id.
    latest: dict[str | None, dict[ObservationType, float]] = defaultdict(dict)
    # Local-day totals of increment types, per scope, for the day recorded in
    # totals_day; restarted when an increment from a later day arrives.
    totals: dict[str | None, dict[str, float]] = defaultdict(dict)
    totals_day: dict[str | None, date] = {}
    plant_latest: dict[str, dict[ObservationType, float]] = defaultdict(dict)
    plant_measured_at: dict[str, datetime] = {}
    harvested_g: dict[str | None, float] = defaultdict(float)
    harvests = sorted(
        (e for e in events if e.event_type == EventType.HARVEST and e.plant_id is None),
        key=lambda e: e.timestamp,
    )
    harvest_index = 0
    boundary: datetime | None = None
    previous: datetime | None = None

    def snapshot(at: datetime) -> GreenhouseState:
        nonlocal harvest_index
        while harvest_index < len(harvests) and harvests[harvest_index].timestamp <= at:
            harvest = harvests[harvest_index]
            harvested_g[harvest.compartment_id] += float(
                harvest.parameters.get("harvested_mass_g", 0.0)
            )
            harvest_index += 1
        compartment_ids = (
            {k for k in latest if k is not None}
            | {k for k in harvested_g if k is not None}
            | {k for k in totals if k is not None}
        )
        snapshot_day = accounting_day(at, timezone)

        def daily(scope: str | None) -> dict[str, float]:
            # a day with no increments yet shows no totals, not yesterday's
            return totals[scope] if totals_day.get(scope) == snapshot_day else {}

        return GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            timestamp=at,
            plant_states=[
                _plant_state(
                    greenhouse_id,
                    plant_id,
                    compartment_id,
                    at,
                    plant_latest[plant_id],
                    plant_measured_at.get(plant_id),
                )
                for plant_id, compartment_id in sorted((plant_compartments or {}).items())
            ],
            environment=GreenhouseEnvironmentState.from_latest_values(latest[None], daily(None)),
            compartments=[
                CompartmentState(
                    compartment_id=compartment_id,
                    environment=GreenhouseEnvironmentState.from_latest_values(
                        latest[compartment_id], daily(compartment_id)
                    ),
                    harvested_total_g=harvested_g[compartment_id],
                )
                for compartment_id in sorted(compartment_ids)
            ],
            greenhouse_harvested_g=harvested_g[None],
        )

    for observation in observations:
        at = observation.timestamp
        if boundary is None:
            boundary = _next_boundary(at, every, timezone)
        elif at > boundary and previous is not None:
            yield snapshot(previous)
            boundary = _next_boundary(at, every, timezone)
        if observation.plant_id is None:
            scope = observation.compartment_id
            field = DAILY_TOTAL_FIELD.get(observation.observation_type)
            if field is None:
                latest[scope][observation.observation_type] = observation.value
            else:
                day = accounting_day(at, timezone)
                if totals_day.get(scope) != day:
                    totals[scope] = {}
                    totals_day[scope] = day
                totals[scope][field] = totals[scope].get(field, 0.0) + observation.value
        else:
            plant_latest[observation.plant_id][observation.observation_type] = observation.value
            plant_measured_at[observation.plant_id] = at
        previous = at

    if previous is not None:
        yield snapshot(previous)


def _plant_state(
    greenhouse_id: str,
    plant_id: str,
    compartment_id: str | None,
    at: datetime,
    latest: dict[ObservationType, float],
    measured_at: datetime | None,
) -> PlantState:
    ripe = latest.get(ObservationType.RIPE_FRUIT_COUNT)
    state = PlantState(
        plant_id=plant_id,
        greenhouse_id=greenhouse_id,
        compartment_id=compartment_id,
        timestamp=at,
        health=PlantHealth.UNKNOWN,
        latest_ripe_fruit_count=int(ripe) if ripe is not None else None,
        last_measured_at=measured_at,
    )
    readings = {
        field: latest[observation_type]
        for observation_type, field in _PLANT_FIELD.items()
        if observation_type in latest
    }
    return state.model_copy(update=readings)


def _next_boundary(at: datetime, every: timedelta, timezone: tzinfo) -> datetime:
    """The first checkpoint instant strictly after `at`."""
    local = at.astimezone(timezone)
    day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if every >= timedelta(days=1):
        candidate = day_start + every
        # a DST day is 23 or 25 hours long; re-anchor to local midnight
        candidate = candidate.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        elapsed = local - day_start
        steps = int(elapsed // every) + 1
        candidate = day_start + every * steps
    return candidate.astimezone(UTC)


def _batched[T](source: Iterable[T], size: int) -> Iterator[list[T]]:
    iterator = iter(source)
    while batch := list(islice(iterator, size)):
        yield batch
