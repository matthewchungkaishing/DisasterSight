"""Pure layout helpers for the Scene Explorer image viewer.

No Streamlit or HTML dependencies — safe for unit tests and reuse.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_PANE_HEIGHT_PX = 420
DEFAULT_HEADER_HEIGHT_PX = 44
DEFAULT_ESTIMATED_CONTAINER_WIDTH_PX = 960
DEFAULT_PANE_COUNT = 2
DEFAULT_GRID_PADDING_PX = 24


@dataclass(frozen=True)
class SceneViewerLayout:
    """Resolved dimensions for a paired scene viewer iframe."""

    max_pane_height_px: int
    pane_display_height_px: int
    component_height_px: int
    header_height_px: int
    pane_aspect_width: int
    pane_aspect_height: int
    pane_count: int = DEFAULT_PANE_COUNT

    @property
    def pane_aspect_css(self) -> str:
        """CSS ``aspect-ratio`` numerator/denominator pair."""
        return f"{self.pane_aspect_width} / {self.pane_aspect_height}"


def compute_pane_display_height(
    image_width: int,
    image_height: int,
    *,
    pane_width_px: float,
    max_pane_height_px: int,
) -> int:
    """Scale image to fit pane width, capped by *max_pane_height_px* (no crop)."""
    if image_width <= 0 or image_height <= 0:
        return max_pane_height_px
    natural_height = pane_width_px * image_height / image_width
    return max(1, min(round(natural_height), max_pane_height_px))


def compute_scene_viewer_layout(
    image_width: int,
    image_height: int,
    *,
    max_pane_height_px: int = DEFAULT_MAX_PANE_HEIGHT_PX,
    header_height_px: int = DEFAULT_HEADER_HEIGHT_PX,
    estimated_container_width_px: int = DEFAULT_ESTIMATED_CONTAINER_WIDTH_PX,
    pane_count: int = DEFAULT_PANE_COUNT,
    grid_padding_px: int = DEFAULT_GRID_PADDING_PX,
) -> SceneViewerLayout:
    """Derive iframe height from image aspect ratio and display caps."""
    safe_width = max(image_width, 1)
    safe_height = max(image_height, 1)
    pane_width_px = estimated_container_width_px / max(pane_count, 1)
    pane_display_height_px = compute_pane_display_height(
        safe_width,
        safe_height,
        pane_width_px=pane_width_px,
        max_pane_height_px=max_pane_height_px,
    )
    component_height_px = header_height_px + pane_display_height_px + grid_padding_px
    return SceneViewerLayout(
        max_pane_height_px=max_pane_height_px,
        pane_display_height_px=pane_display_height_px,
        component_height_px=component_height_px,
        header_height_px=header_height_px,
        pane_aspect_width=safe_width,
        pane_aspect_height=safe_height,
        pane_count=pane_count,
    )
