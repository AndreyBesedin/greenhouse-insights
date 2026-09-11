"""`greenhouse-data`: the developer entry point for dataset work
(docs/design/wur_real_data_ingestion_replay_plan.md section 15).

    greenhouse-data inventory wur agc4-2024 [--write]
"""

import argparse
import sys
from collections.abc import Sequence

from ingestion.manifests import DatasetManifest, load_manifest, manifest_path, write_manifest
from ingestion.storage.upstream_4tu import build_manifest, fetch_dataset_metadata
from ingestion.wur.datasets import WUR_DATASETS, WurDataset


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
