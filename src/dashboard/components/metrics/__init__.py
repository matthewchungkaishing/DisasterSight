"""Dashboard KPI metrics — models, pure HTML builders, and Streamlit renderers."""

from src.dashboard.components.metrics.builder import (
    build_quadrant_html,
    build_scene_metric_cells,
)
from src.dashboard.components.metrics.models import MetricCell
from src.dashboard.components.metrics.render import (
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
