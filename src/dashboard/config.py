"""Dashboard configuration accessors.

Wraps :func:`src.common.paths.load_config` with dashboard-specific
convenience helpers.  Config is read once and cached for the process
lifetime via :func:`functools.lru_cache`.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from src.common.paths import load_config
from src.common.priority_score import priority_weights_from_config

DASHBOARD_ROOT = Path(__file__).parent


@functools.lru_cache(maxsize=1)
def get_dashboard_config() -> dict[str, Any]:
    """Return the full project config, cached for the process."""
    return load_config()


def get_priority_weights() -> dict[str, float]:
    """Priority-score component weights from config.yaml."""
    return priority_weights_from_config(get_dashboard_config().get("priority_score", {}))


def get_scene_viewer_layout_settings() -> dict[str, Any]:
    """Scene Explorer sizing knobs from config.yaml."""
    dash = get_dashboard_config().get("dashboard", {})
    settings: dict[str, Any] = {
        "estimated_container_width_px": int(dash.get("scene_explorer_estimated_width_px", 880)),
        "grid_padding_px": int(dash.get("scene_explorer_grid_padding_px", 0)),
    }
    raw_max = dash.get("scene_explorer_max_pane_height_px")
    if raw_max is not None:
        settings["max_pane_height_px"] = int(raw_max)
    return settings
