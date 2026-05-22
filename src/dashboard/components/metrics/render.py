"""Streamlit render entry points for dashboard KPI metrics."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components.metrics.builder import (
    build_metrics_row_html,
    build_quadrant_html,
    build_scene_metric_cells,
)


def render_scene_metrics_quadrant(
    total: int,
    priority: float,
    review_count: int,
    class_counts: dict[str, int],
) -> None:
    """Render scene KPIs as a 2x2 quadrant box in the dashboard hero sidebar."""
    cells = build_scene_metric_cells(total, priority, review_count, class_counts)
    st.markdown(build_quadrant_html(cells), unsafe_allow_html=True)


def render_metrics_row(
    total: int,
    priority: float,
    review_count: int,
    class_counts: dict[str, int],
) -> None:
    """Render scene KPIs in a horizontal four-column row."""
    cells = build_scene_metric_cells(total, priority, review_count, class_counts)
    st.markdown(build_metrics_row_html(cells), unsafe_allow_html=True)
