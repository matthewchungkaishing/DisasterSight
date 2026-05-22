"""Scene Explorer viewer package — models, HTML builder, and static assets."""

from src.dashboard.components.scene_viewer.builder import (
    CARD_BACKGROUND,
    build_scene_viewer_html,
    render_scene_viewer,
)
from src.dashboard.components.scene_viewer.encoding import image_to_data_uri
from src.dashboard.components.scene_viewer.models import ImagePane

__all__ = [
    "CARD_BACKGROUND",
    "ImagePane",
    "build_scene_viewer_html",
    "image_to_data_uri",
    "render_scene_viewer",
]
