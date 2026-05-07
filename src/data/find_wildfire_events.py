from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from src.common.paths import get_path_map, load_config


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

SUPPORTED_EXTENSIONS = {".json", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

PRE_IMAGE_KEY = "pre_disaster_image"
POST_IMAGE_KEY = "post_disaster_image"
PRE_JSON_KEY = "pre_disaster_json"
POST_JSON_KEY = "post_disaster_json"


def is_keyword_match(path: Path, keywords: Iterable[str]) -> bool:
    name = path.name.lower()
    return any(keyword in name for keyword in keywords)


def extract_scene_id(path: Path) -> str:
    stem = path.stem
    scene_id = re.sub(r"_(pre|post)_disaster$", "", stem, flags=re.IGNORECASE)
    return scene_id


def classify_file_role(path: Path) -> str | None:
    name = path.name.lower()
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        return None

    if "_pre_disaster" in name:
        if suffix == ".json":
            return PRE_JSON_KEY
        if suffix in IMAGE_EXTENSIONS:
            return PRE_IMAGE_KEY

    if "_post_disaster" in name:
        if suffix == ".json":
            return POST_JSON_KEY
        if suffix in IMAGE_EXTENSIONS:
            return POST_IMAGE_KEY

    return None


def scan_wildfire_files(xbd_root: Path) -> dict[str, dict[str, object]]:
    scenes: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "scene_id": "",
            PRE_IMAGE_KEY: "",
            POST_IMAGE_KEY: "",
            PRE_JSON_KEY: "",
            POST_JSON_KEY: "",
            "matched_files": [],
            "matched_keywords": set(),
        }
    )

    for path in xbd_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if not is_keyword_match(path, WILDFIRE_KEYWORDS):
            continue

        role = classify_file_role(path)
        if role is None:
            continue

        scene_id = extract_scene_id(path)
        record = scenes[scene_id]
        record["scene_id"] = scene_id
        record[role] = str(path)
        record["matched_files"].append(str(path))
        record["matched_keywords"].update(
            keyword for keyword in WILDFIRE_KEYWORDS if keyword in path.name.lower()
        )

    return scenes


def is_complete_scene(record: dict[str, object]) -> bool:
    return all(
        bool(record[key])
        for key in (PRE_IMAGE_KEY, POST_IMAGE_KEY, PRE_JSON_KEY, POST_JSON_KEY)
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

    scenes = scan_wildfire_files(xbd_root)
    print_scene_groups(scenes)
    write_scene_index_csv(output_csv, scenes)
    print_top_complete_scenes(scenes, limit=10)
    print(f"\nSaved wildfire scene summary CSV to: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
