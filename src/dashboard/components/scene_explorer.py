"""Scene explorer component — pre/post disaster image viewer."""

from __future__ import annotations

from typing import Any

from src.dashboard.components.image_viewer import ImagePane, image_to_data_uri, render_scene_viewer
from src.dashboard.components.scene_viewer_layout import compute_scene_viewer_layout
from src.dashboard.config import get_scene_viewer_layout_settings
from src.dashboard.data_loaders import get_scene_image_paths
from src.dashboard.overlays import draw_prediction_overlays, load_display_image


def render(
    scene: dict[str, Any],
    disaster_type: str,
    predictions: list[dict[str, Any]],
    confidence_pct: float,
    show_overlays: bool,
    overlay_opacity: float,
) -> None:
    """Render the hero scene explorer with pre/post imagery."""
    pre_path, post_path = get_scene_image_paths(scene)

    pre_img = load_display_image(pre_path, "Pre-disaster")
    post_img = load_display_image(post_path, "Post-disaster")
    if show_overlays:
        post_img = draw_prediction_overlays(post_img, predictions, opacity=overlay_opacity)

    image_width, image_height = pre_img.size
    layout = compute_scene_viewer_layout(
        image_width,
        image_height,
        **get_scene_viewer_layout_settings(),
    )
    post_label = "Post-disaster + damage overlay" if show_overlays else "Post-disaster"
    render_scene_viewer(
        f"Scene Explorer - {disaster_type}",
        f"Mean confidence: {confidence_pct:.0f}%",
        (
            ImagePane(
                key="pre",
                label="Pre-disaster",
                src=image_to_data_uri(pre_img),
                alt="Pre-disaster satellite scene",
                width=image_width,
                height=image_height,
            ),
            ImagePane(
                key="post",
                label=post_label,
                src=image_to_data_uri(post_img),
                alt="Post-disaster satellite scene",
                width=image_width,
                height=image_height,
            ),
        ),
        layout=layout,
    )
