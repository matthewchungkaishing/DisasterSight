from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.common.constants import OVERLAY_COLORS
from src.dashboard.labels import normalize_label


def _placeholder_image(width: int = 640, height: int = 360, label: str = "No image") -> Image.Image:
    """Generate placeholder when satellite imagery is unavailable."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    if "pre" in label.lower():
        arr[:] = (55, 65, 75)
    else:
        arr[:] = (25, 30, 38)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    draw.text((width // 2 - 60, height // 2 - 10), label, fill=(200, 210, 220))
    return img


def load_display_image(path: Path | None, fallback_label: str) -> Image.Image:
    if path and path.exists():
        return Image.open(path).convert("RGB")
    return _placeholder_image(label=fallback_label)


def _label_color(pred: dict) -> tuple[int, int, int]:
    label = normalize_label(pred.get("predicted_label", "unknown"))
    if pred.get("needs_review"):
        color_hex = OVERLAY_COLORS["review_required"]
    else:
        color_hex = OVERLAY_COLORS.get(label, OVERLAY_COLORS["review_required"])
    return (
        int(color_hex[1:3], 16),
        int(color_hex[3:5], 16),
        int(color_hex[5:7], 16),
    )


def _has_valid_bboxes(predictions: list[dict]) -> bool:
    """Return True when at least one prediction has non-degenerate bbox coordinates."""
    return any(int(pred.get("bbox_x2", 0)) > int(pred.get("bbox_x1", 0)) for pred in predictions)


def draw_bbox_overlays(
    image: Image.Image,
    predictions: list[dict],
    opacity: float = 0.45,
) -> Image.Image:
    """Draw building bounding boxes using real prediction bbox coordinates.

    Coordinates are expected in the pixel space of *image* (i.e., the
    post-disaster scene image as loaded from disk).
    """
    if not predictions:
        return image
    overlay = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = int(255 * opacity)
    iw, ih = image.size

    for pred in predictions:
        x1 = int(pred.get("bbox_x1", 0))
        y1 = int(pred.get("bbox_y1", 0))
        x2 = int(pred.get("bbox_x2", 0))
        y2 = int(pred.get("bbox_y2", 0))
        if x2 <= x1 or y2 <= y1:
            continue
        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(iw, x2), min(ih, y2)
        rgb = _label_color(pred)
        draw.rectangle([x1, y1, x2, y2], fill=(*rgb, alpha), outline=(*rgb, 255), width=2)

    base = image.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def draw_prediction_overlays(
    image: Image.Image,
    predictions: list[dict],
    opacity: float = 0.45,
) -> Image.Image:
    """Draw building bbox overlays when prediction coordinates are available."""
    if not _has_valid_bboxes(predictions):
        return image
    return draw_bbox_overlays(image, predictions, opacity=opacity)
