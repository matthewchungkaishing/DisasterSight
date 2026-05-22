"""Backward-compatible facade for dashboard KPI metrics.

Prefer :mod:`src.dashboard.components.metrics` in new code.
"""

from __future__ import annotations

from src.dashboard.components.metrics import (
    MetricCell,
    build_quadrant_html,
    build_scene_metric_cells,
    render_metrics_row,
    render_scene_metrics_quadrant,
)

__all__ = [
    "MetricCell",
    "build_quadrant_html",
    "build_scene_metric_cells",
    "render_metrics_row",
    "render_scene_metrics_quadrant",
]
