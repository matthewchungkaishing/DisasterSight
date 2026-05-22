from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.common.paths import PROJECT_ROOT, get_path_map, load_config


_LABEL_MAP: dict[str, str] = {
    "no-damage": "no_damage",
    "no_damage": "no_damage",
    "minor-damage": "minor_damage",
    "minor_damage": "minor_damage",
    "major-damage": "major_damage",
    "major_damage": "major_damage",
    "destroyed": "destroyed",
    "un-classified": "unclassified",
    "unclassified": "unclassified",
}

VALID_LABELS = frozenset({"no_damage", "minor_damage", "major_damage", "destroyed"})


def normalise_label(raw: str | None) -> str:
    """Map a raw xBD subtype string to a canonical damage label."""
    if not raw:
        return "unknown"
    return _LABEL_MAP.get(str(raw).strip().lower(), "unknown")

_DISASTER_TYPE_MAP: dict[str, str] = {
    "fire": "wildfire",
    "flooding": "flood",
    "flood": "flood",
    "wind": "hurricane",
    "tornado": "hurricane",
    "tsunami": "flood",
    "volcano": "volcano",
    "earthquake": "earthquake",
}


def normalise_disaster_type(raw: str) -> str:
    return _DISASTER_TYPE_MAP.get(raw.strip().lower(), raw.strip().lower())


# Parse polygons

def parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    text = wkt.strip()
    if not text.upper().startswith("POLYGON"):
        return []

    start = text.find("((")
    end = text.rfind("))")
    if start == -1 or end == -1 or end <= start + 2:
        return []

    outer_ring = text[start + 2 : end].split("),", maxsplit=1)[0]
    points: list[tuple[float, float]] = []

    for pair in outer_ring.split(","):
        parts = pair.strip().split()
        if len(parts) < 2:
            return []
        try:
            x, y = float(parts[0]), float(parts[1])
        except ValueError:
            return []
        points.append((x, y))

    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]

    return points


def polygon_area_pixels(points: list[tuple[float, float]]) -> float:
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


# Helper functions for bounnding box

def polygon_to_bbox(points: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (
        int(math.floor(min(xs))),
        int(math.floor(min(ys))),
        int(math.ceil(max(xs))),
        int(math.ceil(max(ys))),
    )


def pad_and_clamp_bbox(
    bbox: tuple[int, int, int, int],
    padding: int,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Expand a bbox by *padding* pixels on each side, then clamp to image bounds."""
    x1, y1, x2, y2 = bbox
    return (
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(image_width, x2 + padding),
        min(image_height, y2 + padding),
    )

# Crop extraction logic

def extract_crop(
    image: Image.Image,
    bbox: tuple[int, int, int, int],
    target_size: int,
) -> Image.Image:
    """Crop *bbox* from *image* and resize to ``target_size × target_size`` RGB."""
    crop = image.crop(bbox)
    return crop.resize((target_size, target_size), Image.LANCZOS)


def create_masked_crop(
    image: Image.Image,
    polygon_points: list[tuple[float, float]],
    bbox: tuple[int, int, int, int],
    target_size: int,
) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    if len(polygon_points) >= 3:
        draw.polygon(polygon_points, fill=255)
    else:
        x1, y1, x2, y2 = bbox
        draw.rectangle((x1, y1, x2, y2), fill=255)

    # All other pixels black
    base = image.convert("RGB")
    masked = Image.new("RGB", image.size, (0, 0, 0))
    masked.paste(base, mask=mask)

    crop = masked.crop(bbox)
    return crop.resize((target_size, target_size), Image.LANCZOS)


# Load wildfires

def load_wildfire_scenes(xbd_root: Path) -> dict[str, dict[str, Any]]:
    from src.data.find_wildfire_events import (
        is_complete_scene,
        scan_wildfire_files,
    )

    raw = scan_wildfire_files(xbd_root)
    scenes: dict[str, dict[str, Any]] = {}

    for scene_id, rec in raw.items():
        if not is_complete_scene(rec):
            continue
        scenes[scene_id] = {
            "scene_id": scene_id,
            "pre_image":  Path(rec["pre_disaster_image"]),
            "post_image": Path(rec["post_disaster_image"]),
            "pre_json":   Path(rec["pre_disaster_json"]),
            "post_json":  Path(rec["post_disaster_json"]),
        }

    return scenes


def load_scene_metadata(post_json: Path) -> dict[str, Any]:
    with post_json.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("metadata", {})

# Assign splits
# Note here chose .7 vs .15 can change as fits

def assign_event_splits(
    event_names: list[str],
    seed: int = 42,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> dict[str, str]:
    events = sorted(set(event_names))
    rng = random.Random(seed)
    shuffled = events[:]
    rng.shuffle(shuffled)

    n = len(shuffled)
    test_frac = max(0.0, 1.0 - train_frac - val_frac)

    n_test  = max(1, round(n * test_frac))
    n_val   = max(1, round(n * val_frac)) if n >= 3 else 0
    n_train = n - n_val - n_test

    if n_train < 1:
        n_val   = max(0, n_val - 1)
        n_train = n - n_val - n_test

    split_map: dict[str, str] = {}
    for i, ev in enumerate(shuffled):
        if i < n_train:
            split_map[ev] = "train"
        elif i < n_train + n_val:
            split_map[ev] = "val"
        else:
            split_map[ev] = "test"

    return split_map


# Extraction buildings

def extract_building_features(json_path: Path) -> list[dict[str, Any]]:
    with json_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    features = data.get("features", {})
    if isinstance(features, dict):
        xy = features.get("xy", [])
        if isinstance(xy, list):
            return [f for f in xy if isinstance(f, dict)]

    return []


# Extract cropped building images for one scene

def extract_crops_for_scene(
    record: dict[str, Any],
    crops_root: Path,
    split: str,
    *,
    target_size: int = 224,
    padding: int = 12,
    min_area_pixels: float = 32.0,
    save_masked: bool = False,
) -> list[dict[str, Any]]:
    scene_id: str = record["scene_id"]
    pre_img_path: Path = record["pre_image"]
    post_img_path: Path = record["post_image"]
    post_json_path: Path = record["post_json"]

    # Load satellite images
    pre_img = Image.open(pre_img_path).convert("RGB")
    post_img = Image.open(post_img_path).convert("RGB")
    img_w, img_h = pre_img.size  # most of the xBD images are 1024×1024

    # Scene-level metadata
    meta = load_scene_metadata(post_json_path)
    disaster_name: str = meta.get("disaster", scene_id)
    disaster_type: str = normalise_disaster_type(meta.get("disaster_type", "unknown"))

    # Building features from post-disaster JSON
    features = extract_building_features(post_json_path)

    # Per-scene crop output directory
    scene_dir = crops_root / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)

    crop_records: list[dict[str, Any]] = []

    for idx, feat in enumerate(features):
        props: dict[str, Any] = feat.get("properties") or {}

        # Skip non-building features (roads, etc etc)
        ftype = str(props.get("feature_type", "")).strip().lower()
        if ftype and ftype != "building":
            continue

        # Parse polygon
        wkt: str = feat.get("wkt", "")
        polygon_pts = parse_wkt_polygon(wkt)
        if not polygon_pts:
            continue

        # Area filter
        area = polygon_area_pixels(polygon_pts)
        if area < min_area_pixels:
            continue

        # Bounding box
        raw_bbox = polygon_to_bbox(polygon_pts)
        bbox = pad_and_clamp_bbox(raw_bbox, padding, img_w, img_h)
        x1, y1, x2, y2 = bbox

        # Skip very small crops that would be mostly padding or single-pixel
        if (x2 - x1) < 2 or (y2 - y1) < 2:
            continue

        building_id: str = str(
            props.get("uid") or props.get("id") or f"bld_{idx:06d}"
        )
        damage_label: str = normalise_label(
            props.get("subtype") or props.get("damage")
        )

        # Extract and save crops
        pre_crop = extract_crop(pre_img, bbox, target_size)
        post_crop = extract_crop(post_img, bbox, target_size)

        pre_crop_path = scene_dir / f"{building_id}_pre.png"
        post_crop_path = scene_dir / f"{building_id}_post.png"
        pre_crop.save(pre_crop_path)
        post_crop.save(post_crop_path)

        # Build relative paths from the project root for portability
        pre_rel = str(pre_crop_path.relative_to(PROJECT_ROOT))
        post_rel = str(post_crop_path.relative_to(PROJECT_ROOT))
        pre_masked_rel = ""
        post_masked_rel = ""
        
        if save_masked:
            pre_masked = create_masked_crop(pre_img, polygon_pts, bbox, target_size)
            post_masked = create_masked_crop(post_img, polygon_pts, bbox, target_size)
            pm_pre = scene_dir / f"{building_id}_pre_masked.png"
            pm_post = scene_dir / f"{building_id}_post_masked.png"
            pre_masked.save(pm_pre)
            post_masked.save(pm_post)
            pre_masked_rel = str(pm_pre.relative_to(PROJECT_ROOT))
            post_masked_rel = str(pm_post.relative_to(PROJECT_ROOT))

        # Record metadata for this crop (probably can be done better)
        crop_records.append(
            {
                "building_id": building_id,
                "scene_id": scene_id,
                "disaster_name": disaster_name,
                "disaster_type": disaster_type,
                "split": split,
                "damage_label": damage_label,
                "polygon_wkt": wkt,
                "bbox_x1": x1,
                "bbox_y1": y1,
                "bbox_x2": x2,
                "bbox_y2": y2,
                "area_pixels": round(area, 2),
                "crop_width": x2 - x1,
                "crop_height": y2 - y1,
                "pre_crop_path": pre_rel,
                "post_crop_path": post_rel,
                "pre_masked_crop_path": pre_masked_rel,
                "post_masked_crop_path": post_masked_rel,
            }
        )

    return crop_records


# Helper to load config parameters for crop extraction

def get_extraction_config() -> dict[str, Any]:
    """Load crop-extraction parameters from the central project config."""
    cfg = load_config()
    ds = cfg.get("dataset", {})
    return {
        "target_size": int(ds.get("image_size", 224)),
        "padding": int(ds.get("crop_padding_pixels", 12)),
        "min_area_pixels": float(ds.get("min_building_area_pixels", 32)),
        "seed": int(cfg.get("project", {}).get("random_seed", 42)),
        "train_frac": float(ds.get("train_split", 0.70)),
        "val_frac": float(ds.get("val_split", 0.15)),
        "crops_root": get_path_map(cfg)["interim_data_dir"] / "crops",
    }
