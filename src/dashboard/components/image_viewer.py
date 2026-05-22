"""Backward-compatible facade for the Scene Explorer viewer.

Prefer importing from :mod:`src.dashboard.components.scene_viewer` in new code.
"""

from __future__ import annotations

from src.dashboard.components.scene_viewer import (
    CARD_BACKGROUND,
    ImagePane,
    build_scene_viewer_html,
    render_scene_viewer,
)
from src.dashboard.components.scene_viewer.encoding import image_to_data_uri

__all__ = [
    "CARD_BACKGROUND",
    "ImagePane",
    "build_scene_viewer_html",
    "image_to_data_uri",
    "render_scene_viewer",
]
