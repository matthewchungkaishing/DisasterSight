"""Map Explorer bottom panels — rationale and review queue."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.components.map_explorer.models import BOTTOM_PANEL_COLUMN_WEIGHTS
from src.dashboard.components.map_explorer.table_data import filter_and_sort_rows
from src.dashboard.components.review_queue import render as render_review_queue
from src.dashboard.components.review_queue import review_queue_heading
from src.dashboard.navigation import focus_scene
from src.dashboard.priority import rationale_text


def _highest_priority_summary(
    summaries: list[dict[str, Any]],
    filter_mode: str,
    sort_by: str,
) -> dict[str, Any] | None:
    if not summaries:
        return None
    rows = filter_and_sort_rows(summaries, filter_mode, sort_by)
    return rows[0] if rows else summaries[0]


def render_bottom_panels(
    summaries: list[dict[str, Any]],
    filter_mode: str,
    sort_by: str,
) -> None:
    """Render compact rationale and review queue panels with spacing."""
    top = _highest_priority_summary(summaries, filter_mode, sort_by)
    if top is None:
        return

    st.markdown(
        '<div class="ds-map-explorer-bottom" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    rationale_col, queue_col = st.columns(BOTTOM_PANEL_COLUMN_WEIGHTS, gap="large")

    with rationale_col:
        st.markdown(
            '<div class="ds-panel ds-panel--compact ds-panel--map-explorer">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<h3 class="ds-panel-head">⚠ Highest Priority Rationale</h3>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ds-rationale-box ds-rationale-box--compact">'
            f"{rationale_text(top, top.get('disaster_name', ''))}</div>",
            unsafe_allow_html=True,
        )
        if st.button("View Deep Analysis", key="deep_analysis", type="primary"):
            focus_scene(top.get("scene_id", ""), "dashboard")
        st.markdown("</div>", unsafe_allow_html=True)

    with queue_col:
        st.markdown(
            '<div class="ds-panel ds-panel--compact ds-panel--map-explorer">',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<h3 class="ds-panel-head">📋 {review_queue_heading(summaries)}</h3>',
            unsafe_allow_html=True,
        )
        render_review_queue(summaries)
        st.markdown("</div>", unsafe_allow_html=True)
