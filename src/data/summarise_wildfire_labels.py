from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from src.common.paths import get_path_map, load_config
from src.data.xbd import extract_building_annotations, load_json, resolve_scene_file

SCENE_INDEX_NAME = "wildfire_scene_index.csv"
SUMMARY_CSV_NAME = "wildfire_label_summary.csv"
LABEL_COLUMNS = (
    "no_damage",
    "minor_damage",
    "major_damage",
    "destroyed",
    "unclassified",
    "unknown",
)


def load_complete_scene_rows(index_csv_path: Path) -> list[dict[str, str]]:
    complete_rows: list[dict[str, str]] = []
    with index_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if str(row.get("is_complete_scene", "")).strip().lower() == "true":
                complete_rows.append(row)
    return complete_rows


def summarise_scene(scene_row: dict[str, str]) -> dict[str, object]:
    post_json_path = resolve_scene_file(scene_row["post_disaster_json"])
    annotation_data = load_json(post_json_path)
    annotations = extract_building_annotations(annotation_data)

    label_counts = Counter(annotation.label for annotation in annotations)
    total_buildings = len(annotations)
    damaged_total = (
        label_counts["minor_damage"] + label_counts["major_damage"] + label_counts["destroyed"]
    )
    significant_damage_total = label_counts["major_damage"] + label_counts["destroyed"]
    damaged_share = (damaged_total / total_buildings) if total_buildings else 0.0
    significant_damage_share = (
        (significant_damage_total / total_buildings) if total_buildings else 0.0
    )
    label_diversity = sum(1 for label in LABEL_COLUMNS if label_counts[label] > 0)

    summary: dict[str, object] = {
        "scene_id": scene_row["scene_id"],
        "post_disaster_json": str(post_json_path),
        "total_buildings": total_buildings,
        "damaged_total": damaged_total,
        "significant_damage_total": significant_damage_total,
        "damaged_share": round(damaged_share, 4),
        "significant_damage_share": round(significant_damage_share, 4),
        "label_diversity": label_diversity,
    }

    for label in LABEL_COLUMNS:
        summary[label] = label_counts[label]

    return summary


def write_summary_csv(output_path: Path, summaries: list[dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scene_id",
        "post_disaster_json",
        "total_buildings",
        "damaged_total",
        "significant_damage_total",
        "damaged_share",
        "significant_damage_share",
        "label_diversity",
        *LABEL_COLUMNS,
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)


def candidate_sort_key(summary: dict[str, object]) -> tuple[object, ...]:
    total_buildings = int(summary["total_buildings"])
    damaged_total = int(summary["damaged_total"])
    significant_damage_total = int(summary["significant_damage_total"])
    label_diversity = int(summary["label_diversity"])

    return (
        total_buildings >= 20,
        damaged_total > 0,
        significant_damage_total > 0,
        total_buildings,
        label_diversity,
        float(summary["significant_damage_share"]),
        float(summary["damaged_share"]),
        str(summary["scene_id"]),
    )


def print_top_candidates(summaries: list[dict[str, object]], limit: int = 20) -> None:
    ranked = sorted(summaries, key=candidate_sort_key, reverse=True)
    top_rows = ranked[:limit]

    headers = (
        ("scene_id", 28),
        ("buildings", 9),
        ("damaged", 8),
        ("signif", 7),
        ("damaged%", 9),
        ("signif%", 8),
        ("diversity", 9),
        ("no", 4),
        ("minor", 6),
        ("major", 6),
        ("dest", 5),
        ("uncls", 5),
        ("unk", 4),
    )

    print("Top 20 wildfire/bushfire candidate scenes:")
    print(
        " ".join(label.ljust(width) for label, width in headers)
    )
    print(
        " ".join("-" * width for _, width in headers)
    )

    for row in top_rows:
        values = (
            str(row["scene_id"])[:28].ljust(28),
            str(row["total_buildings"]).rjust(9),
            str(row["damaged_total"]).rjust(8),
            str(row["significant_damage_total"]).rjust(7),
            f"{float(row['damaged_share']) * 100:8.1f}%".rjust(9),
            f"{float(row['significant_damage_share']) * 100:7.1f}%".rjust(8),
            str(row["label_diversity"]).rjust(9),
            str(row["no_damage"]).rjust(4),
            str(row["minor_damage"]).rjust(6),
            str(row["major_damage"]).rjust(6),
            str(row["destroyed"]).rjust(5),
            str(row["unclassified"]).rjust(5),
            str(row["unknown"]).rjust(4),
        )
        print(" ".join(values))


def main() -> int:
    config = load_config()
    path_map = get_path_map(config)
    xbd_root = path_map["xbd_root"]
    processed_data_dir = path_map["processed_data_dir"]
    index_csv_path = processed_data_dir / SCENE_INDEX_NAME
    output_csv_path = processed_data_dir / SUMMARY_CSV_NAME

    if not xbd_root.exists():
        print(f"Configured xBD root does not exist: {xbd_root}", file=sys.stderr)
        return 1

    if not index_csv_path.exists():
        print(f"Scene index CSV does not exist: {index_csv_path}", file=sys.stderr)
        return 1

    scene_rows = load_complete_scene_rows(index_csv_path)
    summaries = [summarise_scene(scene_row) for scene_row in scene_rows]
    summaries.sort(key=lambda row: str(row["scene_id"]))
    write_summary_csv(output_csv_path, summaries)

    print(f"Saved wildfire label summary CSV to: {output_csv_path.resolve()}")
    print_top_candidates(summaries, limit=20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
