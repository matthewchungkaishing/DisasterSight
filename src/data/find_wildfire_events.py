from __future__ import annotations

import csv
import sys
from pathlib import Path

from src.common.paths import get_path_map, load_config
from src.data.xbd import (
    POST_IMAGE_KEY,
    POST_JSON_KEY,
    PRE_IMAGE_KEY,
    PRE_JSON_KEY,
    is_complete_scene,
    scan_xbd_files,
)

WILDFIRE_KEYWORDS = (
    "wildfire",
    "wildfires",
    "fire",
    "santa",
    "santa-rosa",
    "woolsey",
    "carr",
    "pinery",
    "portugal",
)

def write_scene_index_csv(output_path: Path, scenes: dict[str, dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scene_id",
        PRE_IMAGE_KEY,
        POST_IMAGE_KEY,
        PRE_JSON_KEY,
        POST_JSON_KEY,
        "has_pre_disaster_image",
        "has_post_disaster_image",
        "has_pre_disaster_json",
        "has_post_disaster_json",
        "is_complete_scene",
        "matched_keywords",
        "matched_file_count",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for scene_id in sorted(scenes):
            record = scenes[scene_id]
            writer.writerow(
                {
                    "scene_id": record["scene_id"],
                    PRE_IMAGE_KEY: record[PRE_IMAGE_KEY],
                    POST_IMAGE_KEY: record[POST_IMAGE_KEY],
                    PRE_JSON_KEY: record[PRE_JSON_KEY],
                    POST_JSON_KEY: record[POST_JSON_KEY],
                    "has_pre_disaster_image": bool(record[PRE_IMAGE_KEY]),
                    "has_post_disaster_image": bool(record[POST_IMAGE_KEY]),
                    "has_pre_disaster_json": bool(record[PRE_JSON_KEY]),
                    "has_post_disaster_json": bool(record[POST_JSON_KEY]),
                    "is_complete_scene": is_complete_scene(record),
                    "matched_keywords": "|".join(sorted(record["matched_keywords"])),
                    "matched_file_count": len(record["matched_files"]),
                }
            )


def print_scene_groups(scenes: dict[str, dict[str, object]]) -> None:
    if not scenes:
        print("No wildfire-related xBD files were found from the configured dataset root.")
        return

    print("Wildfire-related files grouped by scene ID:")
    for scene_id in sorted(scenes):
        record = scenes[scene_id]
        print(f"\nScene: {scene_id}")
        print(f"  matched_keywords: {', '.join(sorted(record['matched_keywords']))}")
        print(f"  has_pre_disaster_image: {bool(record[PRE_IMAGE_KEY])}")
        print(f"  has_post_disaster_image: {bool(record[POST_IMAGE_KEY])}")
        print(f"  has_pre_disaster_json: {bool(record[PRE_JSON_KEY])}")
        print(f"  has_post_disaster_json: {bool(record[POST_JSON_KEY])}")
        for file_path in sorted(record["matched_files"]):
            print(f"  - {file_path}")


def print_top_complete_scenes(scenes: dict[str, dict[str, object]], limit: int = 10) -> None:
    complete_scenes = [
        scenes[scene_id] for scene_id in sorted(scenes) if is_complete_scene(scenes[scene_id])
    ]

    print(f"\nTop {min(limit, len(complete_scenes))} complete wildfire scenes:")
    if not complete_scenes:
        print("  No complete wildfire scenes found.")
        return

    for record in complete_scenes[:limit]:
        print(
            "  "
            f"{record['scene_id']} | "
            f"keywords={','.join(sorted(record['matched_keywords']))} | "
            f"files={len(record['matched_files'])}"
        )


def main() -> int:
    config = load_config()
    path_map = get_path_map(config)
    xbd_root = path_map["xbd_root"]
    output_csv = path_map["processed_data_dir"] / "wildfire_scene_index.csv"

    if not xbd_root.exists():
        print(f"Configured xBD root does not exist: {xbd_root}", file=sys.stderr)
        return 1

    scenes = scan_xbd_files(xbd_root, keywords=WILDFIRE_KEYWORDS)
    print_scene_groups(scenes)
    write_scene_index_csv(output_csv, scenes)
    print_top_complete_scenes(scenes, limit=10)
    print(f"\nSaved wildfire scene summary CSV to: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
