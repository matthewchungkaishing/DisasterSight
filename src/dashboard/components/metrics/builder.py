"""Pure HTML builders for dashboard KPI layouts."""

from __future__ import annotations

import html

from src.dashboard.components.damage_badge import render_html
from src.dashboard.components.metrics.models import MetricCell
from src.dashboard.styles import icon

_QUADRANT_ORDER = (
    "total_buildings",
    "priority_score",
    "review_count",
    "dominant_class",
)


def build_scene_metric_cells(
    total: int,
    priority: float,
    review_count: int,
    class_counts: dict[str, int],
) -> tuple[MetricCell, MetricCell, MetricCell, MetricCell]:
    """Build the four scene-level KPI cells for the dashboard sidebar."""
    dominant_html = ""
    if class_counts:
        dom_key = max(class_counts, key=lambda k: class_counts[k])
        dominant_html = render_html(dom_key)

    trending = icon("trending_up", size=20)
    return (
        MetricCell("total_buildings", "Total buildings", str(total)),
        MetricCell(
            "priority_score",
            "Demo Priority Score",
            f"{int(priority)} {trending}",
            value_class="error",
        ),
        MetricCell(
            "review_count",
            "Flagged for Review",
            str(review_count),
            value_class="secondary",
        ),
        MetricCell("dominant_class", "Dominant Class", dominant_html),
    )


def _ordered_cells(cells: tuple[MetricCell, ...]) -> list[MetricCell]:
    by_key = {cell.key: cell for cell in cells}
    return [by_key[key] for key in _QUADRANT_ORDER if key in by_key]


def render_metric_cell_html(cell: MetricCell, *, variant: str) -> str:
    """Render one KPI cell for *variant* (``quadrant`` or ``grid``)."""
    safe_label = html.escape(cell.label)
    value_classes = "ds-metric-value"
    if cell.value_class:
        value_classes = f"{value_classes} {cell.value_class}"

    if variant == "quadrant":
        safe_key = html.escape(cell.key, quote=True)
        return (
            f'<div class="ds-metrics-quadrant__cell" data-metric="{safe_key}">'
            f'<span class="ds-metric-label">{safe_label}</span>'
            f'<div class="{value_classes}">{cell.value_html}</div>'
            f"</div>"
        )

    return (
        f'<div class="ds-metric-card" data-metric="{html.escape(cell.key, quote=True)}">'
        f'<span class="ds-metric-label">{safe_label}</span>'
        f'<div class="{value_classes}">{cell.value_html}</div>'
        f"</div>"
    )


def build_quadrant_html(cells: tuple[MetricCell, ...]) -> str:
    """Build a single bordered 2x2 quadrant box from four metric cells."""
    inner = "".join(
        render_metric_cell_html(cell, variant="quadrant") for cell in _ordered_cells(cells)
    )
    return (
        '<div class="ds-metrics-quadrant" role="group" '
        'aria-label="Scene summary metrics">'
        f"{inner}</div>"
    )


def build_metrics_row_html(cells: tuple[MetricCell, ...]) -> str:
    """Build a horizontal four-column KPI row (e.g. Analytics page)."""
    inner = "".join(render_metric_cell_html(cell, variant="grid") for cell in cells)
    return f'<div class="ds-metrics-grid">{inner}</div>'
