"""`greenhouse-data`: the developer entry point for dataset work
(docs/design/wur_real_data_ingestion_replay_plan.md section 15).

    greenhouse-data inventory wur agc4-2024 [--write]
    greenhouse-data prepare   wur agc4-2024 --profile tiny|dev|full [--compartment 3.06]
    greenhouse-data load      wur agc4-2024 --compartment 3.06 [--from DATE] [--to DATE]

Data lives under GREENHOUSE_DATA_DIR (default ~/.greenhouse-insights/data);
`load` writes to the application database (GREENHOUSE_DATABASE_URL, same
default as the API).
"""

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from pathlib import Path

from dotenv import load_dotenv

from application.db import create_engine_and_tables
from ingestion.canonical import CanonicalGreenhouse
from ingestion.loader import TimeWindow, load_canonical_greenhouse
from ingestion.manifests import (
    ArtifactKind,
    DatasetManifest,
    load_manifest,
    manifest_path,
    write_manifest,
)
from ingestion.profiles import PROFILES, Profile
from ingestion.storage.layout import DataDirectory
from ingestion.storage.resolver import ArtifactResolver, ArtifactUnavailable, UpstreamHttpMirror
from ingestion.storage.upstream_4tu import build_manifest, fetch_dataset_metadata
from ingestion.wur.agc4_challenge_2024 import build as agc4_2024
from ingestion.wur.agc4_challenge_2024.compartments import COMPARTMENTS, compartment
from ingestion.wur.common.time import WUR_LOCAL_TIMEZONE
from ingestion.wur.datasets import AGC4_CHALLENGE_2024, WUR_DATASETS, WurDataset

DEFAULT_DATABASE_URL = "sqlite:///./data/greenhouse.db"


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    result: int = handler(args)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="greenhouse-data")
    commands = parser.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser(
        "inventory",
        help="query the upstream metadata API and generate/verify a dataset manifest "
        "(metadata only - downloads nothing else)",
    )
    _add_wur_dataset_arguments(inventory)
    inventory.add_argument(
        "--write",
        action="store_true",
        help="write the generated manifest to ingestion/manifests/ (default: only compare)",
    )
    inventory.set_defaults(handler=_inventory)

    prepare = commands.add_parser(
        "prepare",
        help="fetch the artifacts a profile allows and build canonical records "
        "(tiny/dev: tabular data only, never the image archives)",
    )
    _add_wur_dataset_arguments(prepare)
    prepare.add_argument("--profile", type=Profile, choices=list(Profile), required=True)
    prepare.add_argument(
        "--compartment",
        action="append",
        choices=sorted(COMPARTMENTS),
        help="2024 compartment(s) to build (default: tiny -> 3.06 only, dev/full -> all)",
    )
    prepare.add_argument("--data-dir", type=Path, default=None, help="override GREENHOUSE_DATA_DIR")
    prepare.set_defaults(handler=_prepare)

    load = commands.add_parser(
        "load",
        help="load one prepared compartment into the application database with "
        "checkpointed state snapshots (replaces any previous load of it)",
    )
    _add_wur_dataset_arguments(load)
    load.add_argument("--compartment", choices=sorted(COMPARTMENTS), required=True)
    load.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    load.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    load.add_argument(
        "--checkpoint-hours",
        type=float,
        default=24.0,
        help="cadence of reconstructed state snapshots (default: one per local day)",
    )
    load.add_argument("--data-dir", type=Path, default=None, help="override GREENHOUSE_DATA_DIR")
    load.add_argument("--database-url", default=None, help="override GREENHOUSE_DATABASE_URL")
    load.set_defaults(handler=_load)

    return parser


def _add_wur_dataset_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("provider", choices=["wur"])
    parser.add_argument("dataset", choices=sorted(WUR_DATASETS))


def _wur_dataset(args: argparse.Namespace) -> WurDataset:
    return WUR_DATASETS[args.dataset]


def _inventory(args: argparse.Namespace) -> int:
    dataset = _wur_dataset(args)
    metadata = fetch_dataset_metadata(dataset.dataset_uuid)
    generated = build_manifest(
        dataset_id=dataset.id,
        dataset_uuid=dataset.dataset_uuid,
        classify=dataset.classify,
        metadata=metadata,
    )
    _print_manifest(generated)

    path = manifest_path(dataset.id)
    if args.write:
        write_manifest(generated)
        print(f"\nwrote {path}")
        return 0
    if not path.exists():
        print(f"\nno committed manifest at {path}; re-run with --write to create it")
        return 1
    committed = load_manifest(dataset.id)
    if committed == generated:
        print(f"\ncommitted manifest {path} matches upstream")
        return 0
    print(f"\ncommitted manifest {path} differs from upstream; re-run with --write to update")
    return 1


def _print_manifest(manifest: DatasetManifest) -> None:
    total = sum(artifact.size_bytes for artifact in manifest.artifacts)
    print(f"{manifest.title} (v{manifest.version}, {manifest.licence}, doi:{manifest.source.doi})")
    for artifact in manifest.artifacts:
        print(
            f"  {artifact.kind.value:18} {_human_size(artifact.size_bytes):>10}  "
            f"md5={artifact.md5}  {artifact.name}"
        )
    print(f"  total {_human_size(total)} compressed")


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


if __name__ == "__main__":
    sys.exit(main())


def _require_2024(dataset: WurDataset) -> None:
    if dataset is not AGC4_CHALLENGE_2024:
        raise SystemExit(
            f"{dataset.cli_name}: only the 2024 challenge dataset has an adapter so far"
        )


def _prepare(args: argparse.Namespace) -> int:
    dataset = _wur_dataset(args)
    _require_2024(dataset)
    rules = PROFILES[args.profile]
    manifest = load_manifest(dataset.id)
    data_dir = DataDirectory(args.data_dir)
    resolver = ArtifactResolver(
        data_dir, mirrors=[UpstreamHttpMirror()], max_download_bytes=rules.max_download_bytes
    )

    print(f"profile {rules.profile.value}: data directory {data_dir.root}")
    for artifact in manifest.artifacts:
        if artifact.kind not in rules.artifact_kinds:
            print(f"  skip   {artifact.name} ({artifact.kind.value}: not part of this profile)")
            continue
        try:
            path = resolver.resolve(manifest, artifact.name)
        except ArtifactUnavailable as error:
            print(f"  error  {error}")
            return 1
        print(f"  ready  {path}")

    if ArtifactKind.TIMESERIES not in rules.artifact_kinds:
        return 0
    numbers = args.compartment or (
        ["3.06"] if rules.profile == Profile.TINY else sorted(COMPARTMENTS)
    )
    for number in numbers:
        canonical = agc4_2024.build_compartment(data_dir, resolver, compartment(number))
        provenance = canonical.provenance()
        print(
            f"  built  {canonical.directory} "
            f"({provenance.observation_count:,} observations, {provenance.event_count} events, "
            f"{provenance.first_timestamp} .. {provenance.last_timestamp})"
        )
    return 0


def _load(args: argparse.Namespace) -> int:
    dataset = _wur_dataset(args)
    _require_2024(dataset)
    data_dir = DataDirectory(args.data_dir)
    target = compartment(args.compartment)
    directory = agc4_2024.canonical_directory(data_dir, target)
    if not directory.exists():
        print(
            f"no canonical data at {directory}; run "
            f"`greenhouse-data prepare wur {dataset.cli_name} --profile tiny --compartment "
            f"{target.number}` first"
        )
        return 1

    window = TimeWindow(
        start=_local_day_start(args.start) if args.start else None,
        end=_local_day_end(args.end) if args.end else None,
    )
    engine = create_engine_and_tables(args.database_url or _database_url())
    report = load_canonical_greenhouse(
        engine,
        CanonicalGreenhouse(directory),
        window=window,
        checkpoint_every=timedelta(hours=args.checkpoint_hours),
        checkpoint_timezone=WUR_LOCAL_TIMEZONE,
    )
    print(
        f"loaded {report.greenhouse_id}: {report.observations:,} observations, "
        f"{report.events} events, {report.snapshots} state snapshots "
        f"({report.first_timestamp} .. {report.last_timestamp})"
    )
    return 0


def _database_url() -> str:
    load_dotenv()
    return os.environ.get("GREENHOUSE_DATABASE_URL", DEFAULT_DATABASE_URL)


def _local_day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=WUR_LOCAL_TIMEZONE)


def _local_day_end(day: date) -> datetime:
    return datetime.combine(day, time.max, tzinfo=WUR_LOCAL_TIMEZONE)
