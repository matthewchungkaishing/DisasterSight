from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.common.paths import PROJECT_ROOT, get_path_map, load_config
from src.data.xbd import (
    BuildingAnnotation,
    extract_building_annotations,
    load_json,
    resolve_scene_file,
)

DEFAULT_SCENE_ID = "pinery-bushfire_00000000"
SCENE_INDEX_NAME = "wildfire_scene_index.csv"
FALLBACK_FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

COLOR_BY_LABEL = {
    "no_damage": "#4CAF50",
    "minor_damage": "#FFC107",
    "major_damage": "#FF7043",
    "destroyed": "#C62828",
    "unclassified": "#808080",
    "unknown": "#808080",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview an xBD scene and overlay post-disaster building annotations."
    )
    parser.add_argument(
        "--scene-id",
        default=DEFAULT_SCENE_ID,
        help=f"xBD scene identifier to preview. Default: {DEFAULT_SCENE_ID}",
    )
    return parser.parse_args()


def load_scene_row(index_csv_path: Path, scene_id: str) -> dict[str, str]:
    with index_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("scene_id") == scene_id:
                return row

    raise ValueError(f"Scene '{scene_id}' was not found in {index_csv_path}.")


def draw_annotations(image: Image.Image, annotations: list[BuildingAnnotation]) -> Image.Image:
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()

    for annotation in annotations:
        color = COLOR_BY_LABEL.get(annotation.label, COLOR_BY_LABEL["unknown"])
        x1, y1, x2, y2 = annotation.bbox_xyxy

        if len(annotation.polygon_xy) >= 3:
            draw.polygon(annotation.polygon_xy, outline=color, width=2)
        else:
            draw.rectangle((x1, y1, x2, y2), outline=color, width=2)

        label_text = annotation.label
        if (x2 - x1) >= 28 and (y2 - y1) >= 12:
            text_anchor = (x1, max(0, y1 - 12))
            text_box = draw.textbbox(text_anchor, label_text, font=font)
            draw.rectangle(text_box, fill="black")
            draw.text(text_anchor, label_text, fill=color, font=font)

    if not annotations:
        notice = "No drawable building annotations found"
        text_box = draw.textbbox((12, 12), notice, font=font)
        draw.rectangle(text_box, fill="black")
        draw.text((12, 12), notice, fill="white", font=font)

    return annotated


def compose_preview(pre_image: Image.Image, post_image: Image.Image) -> Image.Image:
    font = ImageFont.load_default()
    title_height = 24
    spacer = 12
    width = pre_image.width + post_image.width + spacer
    height = max(pre_image.height, post_image.height) + title_height
    canvas = Image.new("RGB", (width, height), color="white")
    canvas.paste(pre_image.convert("RGB"), (0, title_height))
    canvas.paste(post_image.convert("RGB"), (pre_image.width + spacer, title_height))

    draw = ImageDraw.Draw(canvas)
    draw.text((8, 4), "Pre-disaster", fill="black", font=font)
    draw.text(
        (pre_image.width + spacer + 8, 4),
        "Post-disaster with annotations",
        fill="black",
        font=font,
    )
    return canvas


def print_summary(
    scene_id: str,
    pre_image_path: Path,
    post_image_path: Path,
    annotations: list[BuildingAnnotation],
) -> None:
    label_counts = Counter(annotation.label for annotation in annotations)

    print(f"scene_id: {scene_id}")
    print(f"pre_image_path: {pre_image_path}")
    print(f"post_image_path: {post_image_path}")
    print(f"number_of_buildings: {len(annotations)}")
    print(f"damage_label_counts: {dict(sorted(label_counts.items()))}")
    print("first_5_polygon_examples:")

    for annotation in annotations[:5]:
        print(
            "  "
            f"{annotation.building_id} | "
            f"label={annotation.label} | "
            f"bbox={annotation.bbox_xyxy} | "
            f"geometry_source={annotation.geometry_source}"
        )

    if not annotations:
        print("  No building annotations were extracted from the post-disaster JSON.")


def ensure_scene_files_exist(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required scene files: {missing}")


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = get_path_map(config)

    xbd_root = path_map["xbd_root"]
    processed_data_dir = path_map["processed_data_dir"]
    index_csv_path = processed_data_dir / SCENE_INDEX_NAME

    if not xbd_root.exists():
        print(f"Configured xBD root does not exist: {xbd_root}", file=sys.stderr)
        return 1

    if not index_csv_path.exists():
        print(f"Scene index CSV does not exist: {index_csv_path}", file=sys.stderr)
        return 1

    try:
        scene_row = load_scene_row(index_csv_path, args.scene_id)
        pre_image_path = resolve_scene_file(scene_row["pre_disaster_image"])
        post_image_path = resolve_scene_file(scene_row["post_disaster_image"])
        pre_json_path = resolve_scene_file(scene_row["pre_disaster_json"])
        post_json_path = resolve_scene_file(scene_row["post_disaster_json"])
        ensure_scene_files_exist([pre_image_path, post_image_path, pre_json_path, post_json_path])
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    annotation_data = load_json(post_json_path)
    annotations = extract_building_annotations(annotation_data)

    print_summary(args.scene_id, pre_image_path, post_image_path, annotations)

    with Image.open(pre_image_path) as pre_image, Image.open(post_image_path) as post_image:
        annotated_post = draw_annotations(post_image, annotations)
        preview_image = compose_preview(pre_image, annotated_post)

    output_dir = path_map.get("figures_dir", FALLBACK_FIGURES_DIR) / "scene_previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.scene_id}_preview.png"
    preview_image.save(output_path)
    print("Saved preview image to:")
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
