from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import project_relative_path, resolve_path

SUPPORTED_EXTENSIONS = {".json", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

PRE_IMAGE_KEY = "pre_disaster_image"
POST_IMAGE_KEY = "post_disaster_image"
PRE_JSON_KEY = "pre_disaster_json"
POST_JSON_KEY = "post_disaster_json"
SCENE_FILE_KEYS = (PRE_IMAGE_KEY, POST_IMAGE_KEY, PRE_JSON_KEY, POST_JSON_KEY)

LABEL_ALIASES = {
    "no-damage": "no_damage",
    "no damage": "no_damage",
    "no_damage": "no_damage",
    "minor-damage": "minor_damage",
    "minor damage": "minor_damage",
    "minor_damage": "minor_damage",
    "major-damage": "major_damage",
    "major damage": "major_damage",
    "major_damage": "major_damage",
    "destroyed": "destroyed",
    "un-classified": "unclassified",
    "unclassified": "unclassified",
    "unknown": "unknown",
}

DISASTER_TYPE_KEYWORDS = {
    "wildfire": ("wildfire", "bushfire", "fire", "santa-rosa", "woolsey", "carr", "pinery"),
    "earthquake": ("earthquake",),
    "flood": ("flood", "flooding"),
    "hurricane": ("hurricane", "cyclone", "typhoon"),
    "tornado": ("tornado",),
    "tsunami": ("tsunami",),
    "volcano": ("volcano", "volcanic"),
}


@dataclass(frozen=True)
class BuildingAnnotation:
    building_id: str
    label: str
    bbox_xyxy: tuple[int, int, int, int]
    polygon_xy: list[tuple[float, float]]
    geometry_source: str

    @property
    def area_pixels(self) -> int:
        if len(self.polygon_xy) >= 3:
            return int(round(abs(_shoelace_area(self.polygon_xy))))

        x1, y1, x2, y2 = self.bbox_xyxy
        return max(0, x2 - x1) * max(0, y2 - y1)


def is_keyword_match(path: Path, keywords: Iterable[str]) -> bool:
    name = path.name.lower()
    return any(keyword.lower() in name for keyword in keywords)


def extract_scene_id(path: Path) -> str:
    stem = path.stem
    return re.sub(r"_(pre|post)_disaster$", "", stem, flags=re.IGNORECASE)


def extract_disaster_name(scene_id: str) -> str:
    return re.sub(r"_\d+$", "", scene_id)


def infer_disaster_type(scene_id: str) -> str:
    text = scene_id.lower()
    for disaster_type, keywords in DISASTER_TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return disaster_type
    return "unknown"


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


def empty_scene_record(scene_id: str = "") -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "disaster_name": extract_disaster_name(scene_id) if scene_id else "",
        "disaster_type": infer_disaster_type(scene_id) if scene_id else "unknown",
        PRE_IMAGE_KEY: "",
        POST_IMAGE_KEY: "",
        PRE_JSON_KEY: "",
        POST_JSON_KEY: "",
        "matched_files": [],
        "matched_keywords": set(),
    }


def scan_xbd_files(
    xbd_root: Path,
    keywords: Iterable[str] | None = None,
) -> dict[str, dict[str, object]]:
    scenes: dict[str, dict[str, object]] = defaultdict(empty_scene_record)
    keyword_list = tuple(keyword.lower() for keyword in keywords) if keywords else ()

    for path in xbd_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if keyword_list and not is_keyword_match(path, keyword_list):
            continue

        role = classify_file_role(path)
        if role is None:
            continue

        scene_id = extract_scene_id(path)
        record = scenes[scene_id]
        if not record["scene_id"]:
            record.update(empty_scene_record(scene_id))

        record[role] = project_relative_path(path)
        record["matched_files"].append(project_relative_path(path))
        if keyword_list:
            record["matched_keywords"].update(
                keyword for keyword in keyword_list if keyword in path.name.lower()
            )

    return dict(scenes)


def is_complete_scene(record: dict[str, object]) -> bool:
    return all(bool(record.get(key)) for key in SCENE_FILE_KEYS)


def resolve_scene_file(path_value: str) -> Path:
    if not path_value:
        raise ValueError("Encountered an empty scene file path in the scene index.")
    return resolve_path(path_value)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalise_label(label: str | None) -> str:
    if not label:
        return "unknown"

    cleaned = str(label).strip().lower().replace("_", "-")
    canonical = LABEL_ALIASES.get(cleaned, "unknown")
    if canonical in DAMAGE_CLASSES or canonical in {"unclassified", "unknown"}:
        return canonical
    return "unknown"


def coerce_feature_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested_features = value.get("features")
        if isinstance(nested_features, list):
            return [item for item in nested_features if isinstance(item, dict)]
    return []


def extract_candidate_features(annotation_data: dict[str, Any]) -> list[dict[str, Any]]:
    features = annotation_data.get("features")
    if isinstance(features, dict):
        xy_features = coerce_feature_list(features.get("xy"))
        if xy_features:
            return xy_features

        lng_lat_features = coerce_feature_list(features.get("lng_lat"))
        if lng_lat_features:
            return lng_lat_features

    return coerce_feature_list(features)


def extract_polygon_points(feature: dict[str, Any]) -> tuple[list[tuple[float, float]], str]:
    geometry = feature.get("geometry")
    if isinstance(geometry, dict):
        polygon_points = polygon_points_from_coordinates(geometry.get("coordinates"))
        if polygon_points:
            return polygon_points, "geometry"

    wkt_value = feature.get("wkt")
    if isinstance(wkt_value, str) and wkt_value.strip():
        polygon_points = polygon_points_from_wkt(wkt_value)
        if polygon_points:
            return polygon_points, "wkt"

    properties = feature.get("properties")
    if isinstance(properties, dict):
        for key in ("polygon", "polygon_xy", "points"):
            polygon_points = polygon_points_from_coordinates(properties.get(key))
            if polygon_points:
                return polygon_points, f"properties.{key}"

    return [], "missing"


def polygon_points_from_wkt(wkt_value: str) -> list[tuple[float, float]]:
    text = wkt_value.strip()
    if not text or not text.upper().startswith("POLYGON"):
        return []

    start = text.find("((")
    end = text.rfind("))")
    if start == -1 or end == -1 or end <= start + 2:
        return []

    outer_ring = text[start + 2 : end].split("),", maxsplit=1)[0]
    points: list[tuple[float, float]] = []

    for pair in outer_ring.split(","):
        values = pair.strip().split()
        if len(values) < 2:
            return []
        try:
            points.append((float(values[0]), float(values[1])))
        except ValueError:
            return []

    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]

    return points


def polygon_points_from_coordinates(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list) or not value:
        return []

    first = value[0]
    if isinstance(first, list) and first and isinstance(first[0], (list, tuple)):
        return polygon_points_from_coordinates(first)

    points: list[tuple[float, float]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            return []
        try:
            points.append((float(item[0]), float(item[1])))
        except (TypeError, ValueError):
            return []

    return points


def compute_bbox(points: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (
        int(round(min(xs))),
        int(round(min(ys))),
        int(round(max(xs))),
        int(round(max(ys))),
    )


def extract_building_annotations(annotation_data: dict[str, Any]) -> list[BuildingAnnotation]:
    annotations: list[BuildingAnnotation] = []

    for index, feature in enumerate(extract_candidate_features(annotation_data)):
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}

        feature_type = str(properties.get("feature_type", "")).strip().lower()
        if feature_type and feature_type != "building":
            continue

        polygon_points, geometry_source = extract_polygon_points(feature)
        bbox_xyxy: tuple[int, int, int, int] | None = None

        if polygon_points:
            bbox_xyxy = compute_bbox(polygon_points)
        else:
            bbox_value = properties.get("bbox") or feature.get("bbox")
            if isinstance(bbox_value, (list, tuple)) and len(bbox_value) >= 4:
                try:
                    x1, y1, x2, y2 = bbox_value[:4]
                    bbox_xyxy = (
                        int(round(float(x1))),
                        int(round(float(y1))),
                        int(round(float(x2))),
                        int(round(float(y2))),
                    )
                    geometry_source = "bbox"
                except (TypeError, ValueError):
                    bbox_xyxy = None

        if bbox_xyxy is None:
            continue

        label = normalise_label(properties.get("subtype") or properties.get("damage"))
        building_id = str(properties.get("uid") or properties.get("id") or f"building_{index:05d}")
        annotations.append(
            BuildingAnnotation(
                building_id=building_id,
                label=label,
                bbox_xyxy=bbox_xyxy,
                polygon_xy=polygon_points,
                geometry_source=geometry_source,
            )
        )

    return annotations


def _shoelace_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return area / 2.0
