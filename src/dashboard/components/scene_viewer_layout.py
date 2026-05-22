"""Pure layout helpers for the Scene Explorer image viewer.

No Streamlit or HTML dependencies — safe for unit tests and reuse.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_HEADER_HEIGHT_PX = 44
DEFAULT_ESTIMATED_CONTAINER_WIDTH_PX = 960
DEFAULT_PANE_COUNT = 2
DEFAULT_GRID_PADDING_PX = 0


@dataclass(frozen=True)
class SceneViewerLayout:
    """Resolved dimensions for a paired scene viewer iframe."""

    max_pane_height_px: int
    pane_display_height_px: int
    pane_display_width_px: int
    pane_slot_width_px: int
    component_height_px: int
    header_height_px: int
    pane_aspect_width: int
    pane_aspect_height: int
    pane_count: int = DEFAULT_PANE_COUNT

    @property
    def pane_aspect_css(self) -> str:
        """CSS ``aspect-ratio`` numerator/denominator pair."""
        return f"{self.pane_aspect_width} / {self.pane_aspect_height}"

    @property
    def pane_width_css(self) -> str:
        """CSS width for the inner image pane."""
        if self.pane_display_width_px >= self.pane_slot_width_px:
            return "100%"
        return f"{self.pane_display_width_px}px"


def compute_pane_display_height(
    image_width: int,
    image_height: int,
    *,
    pane_width_px: float,
    max_pane_height_px: int,
) -> int:
    """Scale image to fit pane width, capped by *max_pane_height_px* (no crop)."""
    _, height = compute_pane_display_size(
        image_width,
        image_height,
        pane_slot_width_px=pane_width_px,
        max_pane_height_px=max_pane_height_px,
    )
    return height


def compute_pane_display_size(
    image_width: int,
    image_height: int,
    *,
    pane_slot_width_px: float,
    max_pane_height_px: int,
) -> tuple[int, int]:
    """Return inner pane (width, height) that preserves image aspect without cropping."""
    if image_width <= 0 or image_height <= 0:
        return round(pane_slot_width_px), max_pane_height_px

    natural_height = pane_slot_width_px * image_height / image_width
    if natural_height <= max_pane_height_px:
        return round(pane_slot_width_px), max(1, round(natural_height))

    display_height = max_pane_height_px
    display_width = max_pane_height_px * image_width / image_height
    return max(1, round(display_width)), display_height


def compute_scene_viewer_layout(
    image_width: int,
    image_height: int,
    *,
    max_pane_height_px: int | None = None,
    header_height_px: int = DEFAULT_HEADER_HEIGHT_PX,
    estimated_container_width_px: int = DEFAULT_ESTIMATED_CONTAINER_WIDTH_PX,
    pane_count: int = DEFAULT_PANE_COUNT,
    grid_padding_px: int = DEFAULT_GRID_PADDING_PX,
) -> SceneViewerLayout:
    """Derive iframe height from image aspect ratio and display caps.

    When *max_pane_height_px* is ``None`` (the default), the cap is set to
    the computed slot width so that square / portrait images fill the
    available slot without dead-space padding.
    """
    safe_width = max(image_width, 1)
    safe_height = max(image_height, 1)
    pane_slot_width_px = estimated_container_width_px / max(pane_count, 1)
    effective_max_height = (
        max_pane_height_px if max_pane_height_px is not None else round(pane_slot_width_px)
    )
    pane_display_width_px, pane_display_height_px = compute_pane_display_size(
        safe_width,
        safe_height,
        pane_slot_width_px=pane_slot_width_px,
        max_pane_height_px=effective_max_height,
    )
    component_height_px = header_height_px + pane_display_height_px + grid_padding_px
    return SceneViewerLayout(
        max_pane_height_px=effective_max_height,
        pane_display_height_px=pane_display_height_px,
        pane_display_width_px=pane_display_width_px,
        pane_slot_width_px=round(pane_slot_width_px),
        component_height_px=component_height_px,
        header_height_px=header_height_px,
        pane_aspect_width=safe_width,
        pane_aspect_height=safe_height,
        pane_count=pane_count,
    )
