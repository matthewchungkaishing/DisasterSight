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


def draw_demo_overlays(
    image: Image.Image,
    predictions: list[dict],
    opacity: float = 0.45,
) -> Image.Image:
    """Draw synthetic building markers when polygon data is unavailable."""
    if not predictions:
        return image
    overlay = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    w, h = overlay.size
    n = len(predictions)
    cols = max(1, int(n**0.5))
    cell_w, cell_h = w // cols, h // max(1, (n + cols - 1) // cols)
    for idx, pred in enumerate(predictions[:24]):
        label = normalize_label(pred.get("predicted_label", "unknown"))
        if pred.get("needs_review"):
            color_hex = OVERLAY_COLORS["review_required"]
        else:
            color_hex = OVERLAY_COLORS.get(label, OVERLAY_COLORS["review_required"])
        rgb = tuple(int(color_hex[i : i + 2], 16) for i in (1, 3, 5))
        row, col = divmod(idx, cols)
        x0 = col * cell_w + 8
        y0 = row * cell_h + 8
        x1 = x0 + cell_w - 16
        y1 = y0 + cell_h - 16
        alpha = int(255 * opacity)
        draw.rectangle(
            [x0, y0, x1, y1],
            fill=(*rgb, alpha),
            outline=(*rgb, 255),
        )
    base = image.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")
