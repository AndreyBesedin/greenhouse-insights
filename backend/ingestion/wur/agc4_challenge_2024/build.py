"""Builds the canonical tier for one 2024 compartment from the raw
time-series archive: resolve the artifact, read its members straight out
of the zip, parse, and write deterministic canonical files."""

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from domain.enums import SourceType
from domain.event import Event
from domain.greenhouse import Greenhouse, GreenhouseLayout
from domain.observation import Observation
from ingestion.canonical import CanonicalGreenhouse, SourceMember, write_canonical_greenhouse
from ingestion.manifests import DatasetManifest, load_manifest
from ingestion.storage.layout import DataDirectory
from ingestion.storage.resolver import ArtifactResolver
from ingestion.wur.agc4_challenge_2024 import (
    DATASET,
    TIMESERIES_ARTIFACT,
    TIMESERIES_MEMBER_PREFIX,
)
from ingestion.wur.agc4_challenge_2024.compartments import Compartment
from ingestion.wur.agc4_challenge_2024.harvest import (
    final_harvest_event,
    read_harvest_workbook,
    sampling_observations,
)
from ingestion.wur.agc4_challenge_2024.timeseries import parse_timeseries

ADAPTER = "ingestion.wur.agc4_challenge_2024"
HARVEST_MEMBER = "Harvest.xlsx"
CROP = "dwarf_tomato"


def manifest() -> DatasetManifest:
    return load_manifest(DATASET.id)


def canonical_directory(data_dir: DataDirectory, compartment: Compartment) -> Path:
    return data_dir.canonical(manifest()) / compartment.greenhouse_id


def build_compartment(
    data_dir: DataDirectory, resolver: ArtifactResolver, compartment: Compartment
) -> CanonicalGreenhouse:
    dataset = manifest()
    artifact = dataset.artifact(TIMESERIES_ARTIFACT)
    archive_path = resolver.resolve(dataset, artifact.name)

    timeseries_member = TIMESERIES_MEMBER_PREFIX + compartment.timeseries_member
    harvest_member = TIMESERIES_MEMBER_PREFIX + HARVEST_MEMBER
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(timeseries_member) as raw:
            observations = list(
                parse_timeseries(io.TextIOWrapper(raw, encoding="utf-8"), compartment)
            )
        workbook = read_harvest_workbook(io.BytesIO(archive.read(harvest_member)))

    observations.extend(sampling_observations(workbook, compartment))
    events: list[Event] = []
    if observations:
        recording_end = max(o.timestamp for o in observations)
        harvest = final_harvest_event(workbook, compartment, harvested_at=recording_end)
        if harvest is not None:
            events.append(harvest)

    return write_canonical_greenhouse(
        canonical_directory(data_dir, compartment),
        greenhouse=_greenhouse(compartment, observations),
        observations=observations,
        events=events,
        dataset_id=dataset.id,
        dataset_version=dataset.version,
        adapter=ADAPTER,
        sources=[
            SourceMember(artifact=artifact.name, artifact_md5=artifact.md5, member=member)
            for member in (timeseries_member, harvest_member)
        ],
        selection={"compartment": compartment.number, "team": compartment.team},
    )


def _greenhouse(compartment: Compartment, observations: list[Observation]) -> Greenhouse:
    # created_at is the start of the recording so the canonical record is a
    # pure function of the source data, not of when the build ran.
    recording_start = min(o.timestamp for o in observations) if observations else datetime.now(UTC)
    return Greenhouse(
        greenhouse_id=compartment.greenhouse_id,
        name=compartment.name,
        description=(
            f"Recorded history of compartment {compartment.number} of the 4th Autonomous "
            f"Greenhouse Challenge (2024), controlled by team {compartment.team}. "
            f"Dwarf tomato; 5-minute climate, control and irrigation channels plus manual "
            f"harvest samples. Source: WUR / 4TU, {DATASET.id}."
        ),
        source_type=SourceType.IMPORTED_DATA,
        crop=CROP,
        layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
        plants=[],
        created_at=recording_start,
    )
