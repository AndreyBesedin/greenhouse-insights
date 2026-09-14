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

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from itertools import islice

from sqlalchemy import Engine

from application.persistence.event_repository import EventRepository
from application.persistence.greenhouse_repository import GreenhouseRepository
from application.persistence.observation_repository import ObservationRepository
from application.persistence.state_repository import StateRepository
from domain.enums import EventType, ObservationType
from domain.event import Event
from domain.observation import Observation
from domain.state import GreenhouseEnvironmentState, GreenhouseState
from ingestion.canonical import CanonicalGreenhouse

_BATCH = 5_000


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
    checkpoint_every: timedelta = timedelta(days=1),
    checkpoint_timezone: tzinfo = UTC,
) -> LoadReport:
    """Replaces whatever the database held for this greenhouse."""
    window = window or TimeWindow()
    greenhouse = canonical.greenhouse()
    greenhouse_id = greenhouse.greenhouse_id

    observations_repo = ObservationRepository(engine)
    events_repo = EventRepository(engine)
    states_repo = StateRepository(engine)
    observations_repo.delete_for_greenhouse(greenhouse_id)
    events_repo.delete_for_greenhouse(greenhouse_id)
    states_repo.delete_for_greenhouse(greenhouse_id)

    events = [e for e in canonical.events() if window.contains(e.timestamp)]
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

    in_window = (o for o in canonical.observations() if window.contains(o.timestamp))
    for state in reconstruct_checkpoints(
        greenhouse_id,
        persisted(in_window),
        events,
        every=checkpoint_every,
        timezone=checkpoint_timezone,
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
) -> Iterator[GreenhouseState]:
    """Walks chronologically ordered observations once, emitting a state at
    the last observation before each checkpoint boundary and at the end.
    Boundaries are aligned to local midnight in `timezone` for daily
    cadences (so a checkpoint is "end of that day" where the greenhouse
    stands), and to `every` multiples within the day otherwise."""
    latest: dict[ObservationType, float] = {}
    harvests = sorted(
        (e for e in events if e.event_type == EventType.HARVEST and e.plant_id is None),
        key=lambda e: e.timestamp,
    )
    harvested_g = 0.0
    harvest_index = 0
    boundary: datetime | None = None
    previous: datetime | None = None

    def snapshot(at: datetime) -> GreenhouseState:
        nonlocal harvested_g, harvest_index
        while harvest_index < len(harvests) and harvests[harvest_index].timestamp <= at:
            harvested_g += float(harvests[harvest_index].parameters.get("harvested_mass_g", 0.0))
            harvest_index += 1
        return GreenhouseState.aggregate(
            greenhouse_id=greenhouse_id,
            timestamp=at,
            plant_states=[],
            environment=GreenhouseEnvironmentState.from_latest_values(latest),
            greenhouse_harvested_g=harvested_g,
        )

    for observation in observations:
        at = observation.timestamp
        if boundary is None:
            boundary = _next_boundary(at, every, timezone)
        elif at > boundary and previous is not None:
            yield snapshot(previous)
            boundary = _next_boundary(at, every, timezone)
        latest[observation.observation_type] = observation.value
        previous = at

    if previous is not None:
        yield snapshot(previous)


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
