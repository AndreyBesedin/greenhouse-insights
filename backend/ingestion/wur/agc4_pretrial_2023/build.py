"""Builds the canonical tier for the 2023 pre-trial greenhouse from the raw
time-series archive: resolve the artifact, read the climate workbook straight
out of the zip together with the weekly crop measurements, parse, and write
one deterministic canonical greenhouse with its single compartment and its
labelled plants, and the destructive samples as events
(docs/design/wur_execution_plan.md E3-E5)."""

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from domain.enums import SourceType
from domain.greenhouse import Greenhouse, GreenhouseLayout, Plant
from domain.observation import Observation
from ingestion.canonical import CanonicalGreenhouse, SourceMember, write_canonical_greenhouse
from ingestion.manifests import DatasetManifest, load_manifest
from ingestion.storage.layout import DataDirectory
from ingestion.storage.resolver import ArtifactResolver
from ingestion.wur.agc4_pretrial_2023 import (
    CLIMATE_MEMBER,
    CROP_MEMBER,
    DATASET,
    DESTRUCTIVE_MEMBER,
    TIMESERIES_ARTIFACT,
)
from ingestion.wur.agc4_pretrial_2023.climate import parse_climate
from ingestion.wur.agc4_pretrial_2023.compartments import COMPARTMENT_ID, GREENHOUSE_ID, compartment
from ingestion.wur.agc4_pretrial_2023.crops import read_crop_measurements
from ingestion.wur.agc4_pretrial_2023.destructive import read_destructive_samples

ADAPTER = "ingestion.wur.agc4_pretrial_2023"
CROP = "dwarf_tomato"


def manifest() -> DatasetManifest:
    return load_manifest(DATASET.id)


def canonical_directory(data_dir: DataDirectory) -> Path:
    return data_dir.canonical(manifest()) / GREENHOUSE_ID


def build_greenhouse(data_dir: DataDirectory, resolver: ArtifactResolver) -> CanonicalGreenhouse:
    dataset = manifest()
    artifact = dataset.artifact(TIMESERIES_ARTIFACT)
    archive_path = resolver.resolve(dataset, artifact.name)
    with zipfile.ZipFile(archive_path) as archive:
        observations = list(parse_climate(io.BytesIO(archive.read(CLIMATE_MEMBER))))
        crops = read_crop_measurements(io.BytesIO(archive.read(CROP_MEMBER)))
        samples = read_destructive_samples(io.BytesIO(archive.read(DESTRUCTIVE_MEMBER)))
    observations.extend(crops.observations)

    return write_canonical_greenhouse(
        canonical_directory(data_dir),
        greenhouse=_greenhouse(observations, crops.plants),
        observations=observations,
        events=samples,
        dataset_id=dataset.id,
        dataset_version=dataset.version,
        adapter=ADAPTER,
        sources=[
            SourceMember(artifact=artifact.name, artifact_md5=artifact.md5, member=member)
            for member in (CLIMATE_MEMBER, CROP_MEMBER, DESTRUCTIVE_MEMBER)
        ],
        selection={"compartments": [COMPARTMENT_ID]},
    )


def _greenhouse(observations: list[Observation], plants: list[Plant]) -> Greenhouse:
    # created_at is the start of the recording so the canonical record is a
    # pure function of the source data, not of when the build ran.
    recording_start = min(o.timestamp for o in observations) if observations else datetime.now(UTC)
    return Greenhouse(
        greenhouse_id=GREENHOUSE_ID,
        name="WUR AGC4 2023 pre-trial",
        description=(
            "Recorded history of the 4th Autonomous Greenhouse Challenge pre-trial (2023) at "
            "the WUR Bleiswijk facility: one compartment of dwarf tomatoes under four light "
            "and two EC treatments, with 5-minute greenhouse climate, site weather and "
            "weekly manual measurements of 40 labelled plants, plus 240 destructively "
            "sampled plants. "
            f"Source: WUR / 4TU, {DATASET.id}."
        ),
        source_type=SourceType.IMPORTED_DATA,
        crop=CROP,
        layout=GreenhouseLayout(kind="compartment", rows=0, columns=0),
        plants=[],
        compartments=[compartment(plants)],
        created_at=recording_start,
    )
