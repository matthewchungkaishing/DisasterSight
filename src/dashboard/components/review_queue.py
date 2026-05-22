from __future__ import annotations

import streamlit as st

from src.dashboard.navigation import focus_scene


def render(summaries: list[dict]) -> None:
    pending = [s for s in summaries if s.get("review_flag_count", 0) > 0]
    if not pending:
        st.markdown('<p style="color:#c2c6d6;font-size:0.88rem">No scenes flagged for review.</p>', unsafe_allow_html=True)
        return

    for item in pending[:4]:
        sid = item.get("scene_id", "")
        name = item.get("disaster_name", "")
        flags = item.get("review_flag_count", 0)
        row_l, row_r = st.columns([3, 1])
        with row_l:
            st.markdown(f"**{sid}**")
            st.caption(f"{name} · {flags} building(s) flagged")
        with row_r:
            if st.button("Start Review", key=f"review_btn_{sid}", use_container_width=True):
                focus_scene(sid, "dashboard")
