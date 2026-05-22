from __future__ import annotations

import streamlit as st


def render(summaries: list[dict]) -> None:
    """Review queue panel for Map Explorer."""
    pending = [s for s in summaries if s.get("review_flag_count", 0) > 0]
    count = len(pending)
    st.markdown(
        f'<div class="ds-panel-title">Review Queue ({count} pending)</div>',
        unsafe_allow_html=True,
    )
    if not pending:
        st.success("No scenes currently flagged for review.")
        return
    for item in pending[:4]:
        sid = item.get("scene_id", "")
        name = item.get("disaster_name", "")
        flags = item.get("review_flag_count", 0)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{sid}** — {name}")
            st.caption(f"{flags} building(s) flagged")
        with col2:
            if st.button("Start Review", key=f"review_{sid}"):
                st.session_state.selected_scene_id = sid
                st.toast(f"Scene {sid} selected — open Dashboard to inspect.")
