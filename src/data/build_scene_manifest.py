from __future__ import annotations

import argparse
import sys

from src.common.paths import get_path_map, load_config
from src.data.manifests import (
    build_event_aware_scene_manifest_rows,
    select_scene_subset,
    write_scene_manifest_csv,
)
from src.data.xbd import scan_xbd_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reproducible xBD scene manifest.")
    parser.add_argument(
        "--output-name",
        default="scene_manifest.csv",
        help="Manifest filename under the configured manifests directory.",
    )
    parser.add_argument(
        "--max-scenes",
        type=int,
        default=None,
        help="Maximum scenes to include while keeping selected events whole.",
    )
    parser.add_argument(
        "--disaster-name",
        action="append",
        default=None,
        help="Disaster/event name to include. May be provided multiple times.",
    )
    parser.add_argument(
        "--disaster-type",
        action="append",
        default=None,
        help="Disaster type to include, such as wildfire or flood. May be provided multiple times.",
    )
    parser.add_argument(
        "--all-scenes",
        action="store_true",
        help="Ignore configured small-subset defaults and include all matching complete scenes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = get_path_map(config)
    dataset_config = config.get("dataset", {})
    project_config = config.get("project", {})

    xbd_root = path_map["xbd_root"]
    manifests_dir = path_map["manifests_dir"]
    output_path = manifests_dir / args.output_name

    if not xbd_root.exists():
        print(f"Configured xBD root does not exist: {xbd_root}", file=sys.stderr)
        return 1

    scenes = scan_xbd_files(xbd_root)
    max_scenes = resolve_max_scenes(args, dataset_config)
    disaster_names = resolve_filter_values(
        args.disaster_name,
        dataset_config.get("small_subset_disaster_names"),
        use_config_defaults=not args.all_scenes,
    )
    disaster_types = resolve_filter_values(
        args.disaster_type,
        dataset_config.get("small_subset_disaster_types"),
        use_config_defaults=not args.all_scenes,
    )
    selected_scenes = select_scene_subset(
        scenes,
        disaster_names=disaster_names,
        disaster_types=disaster_types,
        max_scenes=max_scenes,
        seed=int(project_config.get("random_seed", 42)),
    )
    rows = build_event_aware_scene_manifest_rows(
        selected_scenes,
        train_fraction=float(dataset_config.get("train_split", 0.7)),
        val_fraction=float(dataset_config.get("val_split", 0.15)),
        test_fraction=float(dataset_config.get("test_split", 0.15)),
        seed=int(project_config.get("random_seed", 42)),
    )
    write_scene_manifest_csv(output_path, rows)

    split_counts: dict[str, int] = {}
    for row in rows:
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1

    print(f"Saved scene manifest to: {output_path.resolve()}")
    print(f"Complete scenes: {len(rows)}")
    print(f"Split counts: {dict(sorted(split_counts.items()))}")
    return 0


def resolve_max_scenes(args: argparse.Namespace, dataset_config: dict[str, object]) -> int | None:
    if args.all_scenes:
        return None
    if args.max_scenes is not None:
        return args.max_scenes
    if bool(dataset_config.get("use_small_subset", False)):
        configured_limit = dataset_config.get("small_subset_max_scenes")
        return int(configured_limit) if configured_limit else None
    return None


def resolve_filter_values(
    cli_values: list[str] | None,
    configured_values: object,
    *,
    use_config_defaults: bool,
) -> list[str]:
    if cli_values:
        return cli_values
    if not use_config_defaults:
        return []
    if isinstance(configured_values, list):
        return [str(value) for value in configured_values]
    return []


if __name__ == "__main__":
    raise SystemExit(main())
