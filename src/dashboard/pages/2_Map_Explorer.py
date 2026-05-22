from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import priority_table, review_queue, shell, sidebar
from src.dashboard.data_loaders import load_zone_summaries
from src.dashboard.priority import rationale_text
from src.dashboard.styles import inject_theme

inject_theme()
shell.render_header("default")
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
    sort_by = st.selectbox("Sort", ["Priority Score", "Review count", "Destroyed %"])
with ctrl3:
    page = st.number_input("Page", min_value=0, value=0, step=1, label_visibility="collapsed")

with st.container(border=True):
    priority_table.render_table(summaries, filter_mode, sort_by, page=page)

if summaries:
    top = summaries[0]
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown('<div class="ds-panel-title">⚠ Highest Priority Rationale</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown(rationale_text(top, top.get("disaster_name", "")))
            if st.button("View Deep Analysis", key="deep_analysis", type="primary"):
                st.session_state.selected_scene_id = top.get("scene_id", "")
                st.info("Scene selected — switch to Dashboard to inspect imagery.")
    with c2:
        with st.container(border=True):
            st.markdown(
                f'<div class="ds-panel-title">📋 Review Queue ({sum(1 for s in summaries if s.get("review_flag_count", 0) > 0)} pending)</div>',
                unsafe_allow_html=True,
            )
            review_queue.render(summaries)

shell.render_footer(show_hitl=False)
