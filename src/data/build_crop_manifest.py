from __future__ import annotations

import argparse
import random
import shutil
import sys

from src.common.paths import get_path_map, load_config
from src.data.crop_extraction import (
    extract_crops_for_manifest,
    get_extraction_config,
    read_scene_manifest_csv,
    write_crop_manifest_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract paired xBD building crops.")
    parser.add_argument(
        "--scene-manifest",
        default="scene_manifest.csv",
        help="Scene manifest filename under the configured manifests directory.",
    )
    parser.add_argument(
        "--output-name",
        default="crop_manifest.csv",
        help="Crop manifest filename under the configured manifests directory.",
    )
    parser.add_argument(
        "--save-masked",
        action="store_true",
        help="Also save crops with pixels outside the building polygon masked to black.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing generated crops under the configured crops directory first.",
    )
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=None,
        help=(
            "Maximum crop records to write for each damage class. "
            "Useful for balanced training sets from large xBD downloads."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed used when sampling scenes for --max-per-class.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = get_path_map(config)
    extraction_config = get_extraction_config()

    scene_manifest_path = path_map["manifests_dir"] / args.scene_manifest
    output_path = path_map["manifests_dir"] / args.output_name

    if not scene_manifest_path.exists():
        print(f"Scene manifest does not exist: {scene_manifest_path}", file=sys.stderr)
        print("Run `python -m src.data.build_scene_manifest` first.", file=sys.stderr)
        return 1

    if args.clean:
        clean_crops_root(extraction_config.crops_root, path_map["interim_data_dir"])

    scene_rows = read_scene_manifest_csv(scene_manifest_path)
    if args.max_per_class is not None:
        if args.max_per_class <= 0:
            print("--max-per-class must be positive when provided.", file=sys.stderr)
            return 1
        seed = (
            args.seed
            if args.seed is not None
            else int(config.get("project", {}).get("random_seed", 42))
        )
        random.Random(seed).shuffle(scene_rows)

    crop_records = extract_crops_for_manifest(
        scene_rows,
        extraction_config.crops_root,
        target_size=extraction_config.target_size,
        padding=extraction_config.padding,
        min_area_pixels=extraction_config.min_area_pixels,
        save_masked=args.save_masked,
        max_per_class=args.max_per_class,
    )
    write_crop_manifest_csv(output_path, crop_records)

    print(f"Saved crop manifest to: {output_path.resolve()}")
    print(f"Saved crops under: {extraction_config.crops_root.resolve()}")
    print(f"Crop records: {len(crop_records)}")
    return 0


def clean_crops_root(crops_root, interim_data_dir) -> None:
    """Remove generated crop images without touching raw xBD data."""
    crops_root = crops_root.resolve()
    interim_data_dir = interim_data_dir.resolve()
    if crops_root == interim_data_dir or interim_data_dir not in crops_root.parents:
        raise ValueError(f"Refusing to clean unexpected crop directory: {crops_root}")
    if crops_root.exists():
        shutil.rmtree(crops_root)


if __name__ == "__main__":
    raise SystemExit(main())
