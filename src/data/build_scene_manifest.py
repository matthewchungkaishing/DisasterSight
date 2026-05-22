from __future__ import annotations

import argparse
import sys

from src.common.paths import get_path_map, load_config
from src.data.manifests import (
    build_event_aware_scene_manifest_rows,
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
    rows = build_event_aware_scene_manifest_rows(
        scenes,
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


if __name__ == "__main__":
    raise SystemExit(main())
