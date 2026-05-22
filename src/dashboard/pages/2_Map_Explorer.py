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

st.markdown("## Priority ranking")
st.caption("Zones ordered by demo priority score")

st.markdown(
    '<div class="ds-banner">ℹ Priority scores are generated via algorithmic analysis of '
    "preliminary satellite imagery and are subject to latency and occlusion errors. "
    "Human verification is required prior to resource deployment.</div>",
    unsafe_allow_html=True,
)

summaries = load_zone_summaries()
filter_col, sort_col, page_col = st.columns([2, 2, 1])
with filter_col:
    filter_mode = st.radio(
        "Filter",
        ["All", "Review Required", "Test"],
        horizontal=True,
        label_visibility="collapsed",
    )
with sort_col:
    sort_by = st.selectbox(
        "Sort",
        ["Priority Score", "Review count", "Destroyed %"],
        label_visibility="visible",
    )
with page_col:
    page = st.number_input("Page", min_value=0, value=0, step=1)

priority_table.render_table(summaries, filter_mode, sort_by, page=page)

if summaries:
    top = summaries[0]
    bottom_cols = st.columns(2)
    with bottom_cols[0]:
        st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
        st.markdown("#### Highest Priority Rationale")
        st.markdown(
            rationale_text(top, top.get("disaster_name", "")),
        )
        if st.button("View Deep Analysis", key="deep_analysis"):
            st.session_state.selected_scene_id = top.get("scene_id", "")
            st.info("Scene selected — switch to Dashboard to inspect imagery.")
        st.markdown("</div>", unsafe_allow_html=True)
    with bottom_cols[1]:
        st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
        review_queue.render(summaries)
        st.markdown("</div>", unsafe_allow_html=True)

shell.render_footer(show_hitl=False)
