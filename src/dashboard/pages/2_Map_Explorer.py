"""Map Explorer page — zone priority ranking and review queue."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import priority_table, review_queue, shell, sidebar
from src.dashboard.data_loaders import load_zone_summaries
from src.dashboard.navigation import focus_scene, set_active_page
from src.dashboard.priority import rationale_text

set_active_page("map_explorer")
shell.render_topbar()
sidebar.render_sidebar_extras()

shell.render_page_heading("Priority ranking", "Zones ordered by demo priority score")

st.markdown(
    """
    <div class="ds-banner">
        <strong>Responsible AI Notice</strong>
        Priority scores are generated via algorithmic analysis of preliminary satellite imagery
        and are subject to latency and occlusion errors. Human verification is required prior
        to resource deployment.
    </div>
    """,
    unsafe_allow_html=True,
)

summaries = load_zone_summaries()
ctrl1, ctrl2, ctrl3 = st.columns([2.2, 1.5, 0.8])
with ctrl1:
    filter_mode = st.radio(
        "Filter scenes",
        ["All", "Review Required", "Test"],
        horizontal=True,
        label_visibility="collapsed",
    )
with ctrl2:
    sort_by = st.selectbox(
        "Sort: Priority Score",
        ["Priority Score", "Review count", "Destroyed %"],
    )
with ctrl3:
    page = st.number_input("Page", min_value=0, value=0, step=1, label_visibility="collapsed")

with st.container(border=True):
    priority_table.render_table(summaries, filter_mode, sort_by, page=page)

if summaries:
    top = summaries[0]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
        st.markdown(
            '<h3 class="ds-panel-head">⚠ Highest Priority Rationale</h3>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ds-rationale-box">'
            f"{rationale_text(top, top.get('disaster_name', ''))}</div>",
            unsafe_allow_html=True,
        )
        if st.button("View Deep Analysis", key="deep_analysis", type="primary"):
            focus_scene(top.get("scene_id", ""), "dashboard")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
        pending = sum(1 for s in summaries if s.get("review_flag_count", 0) > 0)
        st.markdown(
            f'<h3 class="ds-panel-head">📋 Review Queue ({pending} pending)</h3>',
            unsafe_allow_html=True,
        )
        review_queue.render(summaries)
        st.markdown("</div>", unsafe_allow_html=True)

shell.render_footer(show_hitl=False)
