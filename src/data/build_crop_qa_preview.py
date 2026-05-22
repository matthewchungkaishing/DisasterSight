from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import PROJECT_ROOT, get_path_map, load_config, resolve_path


def select_preview_rows(
    rows: list[dict[str, str]],
    *,
    per_class: int,
    seed: int,
) -> list[dict[str, str]]:
    """Pick a deterministic sample of crop rows for visual QA."""
    rng = random.Random(seed)
    selected: list[dict[str, str]] = []
    for label in DAMAGE_CLASSES:
        label_rows = [row for row in rows if row.get("damage_label") == label]
        rng.shuffle(label_rows)
        selected.extend(label_rows[:per_class])
    return selected


def build_crop_qa_preview(
    rows: list[dict[str, str]],
    output_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    thumb_size: int = 96,
    per_class: int = 4,
    seed: int = 42,
) -> int:
    """Create a pre/post crop contact sheet for quick manual QA."""
    selected_rows = select_preview_rows(rows, per_class=per_class, seed=seed)
    if not selected_rows:
        raise ValueError("No crop rows available for QA preview.")

    margin = 12
    label_width = 220
    row_height = thumb_size + margin
    width = label_width + thumb_size * 2 + margin * 4
    height = row_height * len(selected_rows) + margin
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    y = margin
    for row in selected_rows:
        label_text = (
            f"{row.get('damage_label', '')}\n"
            f"{row.get('scene_id', '')}\n"
            f"{row.get('building_id', '')}"
        )
        draw.multiline_text((margin, y + 6), label_text, fill=(20, 20, 20), spacing=4)

        pre_crop = _load_crop(row["pre_crop_path"], project_root, thumb_size)
        post_crop = _load_crop(row["post_crop_path"], project_root, thumb_size)
        canvas.paste(pre_crop, (label_width + margin * 2, y))
        canvas.paste(post_crop, (label_width + thumb_size + margin * 3, y))
        y += row_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return len(selected_rows)


def read_crop_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a crop contact sheet for QA.")
    parser.add_argument(
        "--manifest",
        default="crop_manifest.csv",
        help="Crop manifest filename under configured manifests_dir, or an explicit path.",
    )
    parser.add_argument(
        "--output-name",
        default="crop_qa_preview.png",
        help="Preview filename under configured figures_dir.",
    )
    parser.add_argument("--per-class", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = get_path_map(config)
    project_config = config.get("project", {})

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute() and manifest_path.parent == Path("."):
        manifest_path = path_map["manifests_dir"] / manifest_path
    else:
        manifest_path = resolve_path(manifest_path)

    output_path = path_map["figures_dir"] / args.output_name
    rows = read_crop_manifest(manifest_path)
    row_count = build_crop_qa_preview(
        rows,
        output_path,
        per_class=args.per_class,
        seed=int(project_config.get("random_seed", 42)),
    )
    print(f"Saved QA preview to: {output_path.resolve()}")
    print(f"Preview rows: {row_count}")
    return 0


def _load_crop(path_value: str, project_root: Path, thumb_size: int) -> Image.Image:
    path = Path(path_value)
    resolved_path = path if path.is_absolute() else project_root / path
    with Image.open(resolved_path) as image:
        return image.convert("RGB").resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    raise SystemExit(main())
