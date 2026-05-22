from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import get_path_map, load_config, project_relative_path, resolve_path
from src.data.xbd import (
    POST_IMAGE_KEY,
    POST_JSON_KEY,
    PRE_IMAGE_KEY,
    BuildingAnnotation,
    extract_building_annotations,
    extract_disaster_name,
    infer_disaster_type,
    load_json,
)

CROP_MANIFEST_FIELDS = (
    "building_id",
    "scene_id",
    "disaster_name",
    "disaster_type",
    "split",
    "damage_label",
    "geometry_source",
    "polygon_xy",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "area_pixels",
    "crop_width",
    "crop_height",
    "pre_crop_path",
    "post_crop_path",
    "pre_masked_crop_path",
    "post_masked_crop_path",
)


@dataclass(frozen=True)
class CropExtractionConfig:
    target_size: int
    padding: int
    min_area_pixels: float
    crops_root: Path


@dataclass(frozen=True)
class CropRecord:
    building_id: str
    scene_id: str
    disaster_name: str
    disaster_type: str
    split: str
    damage_label: str
    geometry_source: str
    polygon_xy: str
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int
    area_pixels: int
    crop_width: int
    crop_height: int
    pre_crop_path: str
    post_crop_path: str
    pre_masked_crop_path: str = ""
    post_masked_crop_path: str = ""


def get_extraction_config() -> CropExtractionConfig:
    """Load crop extraction settings from config.yaml."""
    config = load_config()
    dataset_config = config.get("dataset", {})
    path_map = get_path_map(config)
    return CropExtractionConfig(
        target_size=int(dataset_config.get("image_size", 224)),
        padding=int(dataset_config.get("crop_padding_pixels", 12)),
        min_area_pixels=float(dataset_config.get("min_building_area_pixels", 32)),
        crops_root=path_map["interim_data_dir"] / "crops",
    )


def pad_and_clamp_bbox(
    bbox_xyxy: tuple[int, int, int, int],
    padding: int,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Expand a bbox by padding pixels and clamp it to image bounds."""
    x1, y1, x2, y2 = bbox_xyxy
    return (
        max(0, x1 - padding),
        max(0, y1 - padding),
        min(image_width, x2 + padding),
        min(image_height, y2 + padding),
    )


def extract_crop(
    image: Image.Image,
    bbox_xyxy: tuple[int, int, int, int],
    target_size: int,
) -> Image.Image:
    """Crop a bounding box from an image and resize it to a square RGB crop."""
    return image.crop(bbox_xyxy).resize((target_size, target_size), Image.Resampling.LANCZOS)


def create_masked_crop(
    image: Image.Image,
    annotation: BuildingAnnotation,
    bbox_xyxy: tuple[int, int, int, int],
    target_size: int,
) -> Image.Image:
    """Return a crop where pixels outside the building footprint are black."""
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    if len(annotation.polygon_xy) >= 3:
        draw.polygon(annotation.polygon_xy, fill=255)
    else:
        draw.rectangle(annotation.bbox_xyxy, fill=255)

    masked = Image.new("RGB", image.size, (0, 0, 0))
    masked.paste(image.convert("RGB"), mask=mask)
    return extract_crop(masked, bbox_xyxy, target_size)


def extract_crops_for_scene(
    record: dict[str, Any],
    crops_root: Path,
    *,
    target_size: int = 224,
    padding: int = 12,
    min_area_pixels: float = 32.0,
    save_masked: bool = False,
) -> list[CropRecord]:
    """Extract paired pre/post building crops for one complete xBD scene record."""
    scene_id = str(record["scene_id"])
    pre_image_path = _scene_path(record, "pre_image_path", PRE_IMAGE_KEY)
    post_image_path = _scene_path(record, "post_image_path", POST_IMAGE_KEY)
    post_json_path = _scene_path(record, "post_json_path", "label_json_path", POST_JSON_KEY)

    annotations = extract_building_annotations(load_json(post_json_path))
    scene_output_dir = crops_root / scene_id
    scene_output_dir.mkdir(parents=True, exist_ok=True)

    disaster_name = str(record.get("disaster_name") or extract_disaster_name(scene_id))
    disaster_type = str(record.get("disaster_type") or infer_disaster_type(scene_id))
    split = str(record.get("split") or "")

    crop_records: list[CropRecord] = []
    with Image.open(pre_image_path) as pre_source, Image.open(post_image_path) as post_source:
        pre_image = pre_source.convert("RGB")
        post_image = post_source.convert("RGB")
        image_width, image_height = pre_image.size
        if post_image.size != pre_image.size:
            raise ValueError(f"Pre/post image sizes differ for scene {scene_id}.")

        for annotation in annotations:
            if annotation.label not in DAMAGE_CLASSES or annotation.area_pixels < min_area_pixels:
                continue

            bbox_xyxy = pad_and_clamp_bbox(
                annotation.bbox_xyxy,
                padding,
                image_width,
                image_height,
            )
            x1, y1, x2, y2 = bbox_xyxy
            if x2 <= x1 or y2 <= y1:
                continue

            safe_building_id = _safe_filename(annotation.building_id)
            pre_crop_path = scene_output_dir / f"{safe_building_id}_pre.png"
            post_crop_path = scene_output_dir / f"{safe_building_id}_post.png"

            extract_crop(pre_image, bbox_xyxy, target_size).save(pre_crop_path)
            extract_crop(post_image, bbox_xyxy, target_size).save(post_crop_path)

            pre_masked_path = None
            post_masked_path = None
            if save_masked:
                pre_masked_path = scene_output_dir / f"{safe_building_id}_pre_masked.png"
                post_masked_path = scene_output_dir / f"{safe_building_id}_post_masked.png"
                create_masked_crop(pre_image, annotation, bbox_xyxy, target_size).save(
                    pre_masked_path
                )
                create_masked_crop(post_image, annotation, bbox_xyxy, target_size).save(
                    post_masked_path
                )

            crop_records.append(
                CropRecord(
                    building_id=annotation.building_id,
                    scene_id=scene_id,
                    disaster_name=disaster_name,
                    disaster_type=disaster_type,
                    split=split,
                    damage_label=annotation.label,
                    geometry_source=annotation.geometry_source,
                    polygon_xy=json.dumps(annotation.polygon_xy, separators=(",", ":")),
                    bbox_x1=x1,
                    bbox_y1=y1,
                    bbox_x2=x2,
                    bbox_y2=y2,
                    area_pixels=annotation.area_pixels,
                    crop_width=x2 - x1,
                    crop_height=y2 - y1,
                    pre_crop_path=_portable_path(pre_crop_path),
                    post_crop_path=_portable_path(post_crop_path),
                    pre_masked_crop_path=_portable_path(pre_masked_path) if pre_masked_path else "",
                    post_masked_crop_path=(
                        _portable_path(post_masked_path) if post_masked_path else ""
                    ),
                )
            )

    return crop_records


def extract_crops_for_manifest(
    scene_rows: list[dict[str, str]],
    crops_root: Path,
    *,
    target_size: int = 224,
    padding: int = 12,
    min_area_pixels: float = 32.0,
    save_masked: bool = False,
) -> list[CropRecord]:
    """Extract crops for all scenes in a scene manifest."""
    crop_records: list[CropRecord] = []
    for row in scene_rows:
        crop_records.extend(
            extract_crops_for_scene(
                row,
                crops_root,
                target_size=target_size,
                padding=padding,
                min_area_pixels=min_area_pixels,
                save_masked=save_masked,
            )
        )
    return crop_records


def read_scene_manifest_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_crop_manifest_csv(path: Path, crop_records: list[CropRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CROP_MANIFEST_FIELDS)
        writer.writeheader()
        for crop_record in crop_records:
            writer.writerow(asdict(crop_record))


def _scene_path(record: dict[str, Any], *keys: str) -> Path:
    for key in keys:
        value = record.get(key)
        if value:
            return resolve_path(str(value))
    raise KeyError(f"Scene record is missing one of: {', '.join(keys)}")


def _portable_path(path: Path | None) -> str:
    if path is None:
        return ""
    return project_relative_path(path)


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value)
