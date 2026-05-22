from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import PROJECT_ROOT, get_path_map, load_config, resolve_path
from src.data.crop_extraction import CROP_MANIFEST_FIELDS

REQUIRED_CROP_PATH_FIELDS = ("pre_crop_path", "post_crop_path")
OPTIONAL_CROP_PATH_FIELDS = ("pre_masked_crop_path", "post_masked_crop_path")


@dataclass(frozen=True)
class CropManifestValidationResult:
    manifest_path: Path
    row_count: int
    class_counts: dict[str, int]
    split_counts: dict[str, int]
    missing_required_fields: list[str]
    missing_crop_path_count: int
    invalid_label_count: int
    invalid_bbox_count: int
    missing_split_count: int

    @property
    def passed(self) -> bool:
        return (
            self.row_count > 0
            and not self.missing_required_fields
            and self.missing_crop_path_count == 0
            and self.invalid_label_count == 0
            and self.invalid_bbox_count == 0
            and self.missing_split_count == 0
        )


def validate_crop_manifest(
    manifest_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
) -> CropManifestValidationResult:
    """Validate crop manifest schema, labels, bboxes, splits, and crop file paths."""
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        missing_required_fields = [
            field for field in CROP_MANIFEST_FIELDS if field not in fieldnames
        ]

        rows = list(reader)

    class_counts = Counter(row.get("damage_label", "") for row in rows)
    split_counts = Counter(row.get("split", "") for row in rows)

    missing_crop_path_count = 0
    invalid_label_count = 0
    invalid_bbox_count = 0
    missing_split_count = 0

    for row in rows:
        if row.get("damage_label") not in DAMAGE_CLASSES:
            invalid_label_count += 1
        if not row.get("split"):
            missing_split_count += 1
        if not _has_valid_bbox(row):
            invalid_bbox_count += 1

        for field in REQUIRED_CROP_PATH_FIELDS:
            if not _crop_path_exists(row.get(field, ""), project_root):
                missing_crop_path_count += 1

        for field in OPTIONAL_CROP_PATH_FIELDS:
            value = row.get(field, "")
            if value and not _crop_path_exists(value, project_root):
                missing_crop_path_count += 1

    return CropManifestValidationResult(
        manifest_path=manifest_path,
        row_count=len(rows),
        class_counts=dict(sorted(class_counts.items())),
        split_counts=dict(sorted(split_counts.items())),
        missing_required_fields=missing_required_fields,
        missing_crop_path_count=missing_crop_path_count,
        invalid_label_count=invalid_label_count,
        invalid_bbox_count=invalid_bbox_count,
        missing_split_count=missing_split_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the xBD crop manifest contract.")
    parser.add_argument(
        "--manifest",
        default="crop_manifest.csv",
        help="Crop manifest filename under configured manifests_dir, or an explicit path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = get_path_map(config)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute() and manifest_path.parent == Path("."):
        manifest_path = path_map["manifests_dir"] / manifest_path
    else:
        manifest_path = resolve_path(manifest_path)

    if not manifest_path.exists():
        print(f"Crop manifest does not exist: {manifest_path}")
        return 1

    result = validate_crop_manifest(manifest_path)
    print(f"Manifest: {result.manifest_path.resolve()}")
    print(f"Rows: {result.row_count}")
    print(f"Class counts: {result.class_counts}")
    print(f"Split counts: {result.split_counts}")
    print(f"Missing required fields: {result.missing_required_fields}")
    print(f"Missing crop paths: {result.missing_crop_path_count}")
    print(f"Invalid labels: {result.invalid_label_count}")
    print(f"Invalid bboxes: {result.invalid_bbox_count}")
    print(f"Missing splits: {result.missing_split_count}")
    print(f"Passed: {result.passed}")
    return 0 if result.passed else 1


def _crop_path_exists(path_value: str, project_root: Path) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    resolved_path = path if path.is_absolute() else project_root / path
    return resolved_path.exists()


def _has_valid_bbox(row: dict[str, str]) -> bool:
    try:
        x1 = int(row.get("bbox_x1", ""))
        y1 = int(row.get("bbox_y1", ""))
        x2 = int(row.get("bbox_x2", ""))
        y2 = int(row.get("bbox_y2", ""))
        crop_width = int(row.get("crop_width", ""))
        crop_height = int(row.get("crop_height", ""))
        area_pixels = int(row.get("area_pixels", ""))
    except ValueError:
        return False

    return x2 > x1 and y2 > y1 and crop_width > 0 and crop_height > 0 and area_pixels > 0


if __name__ == "__main__":
    raise SystemExit(main())
