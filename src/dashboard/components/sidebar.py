from __future__ import annotations

import streamlit as st

from src.common.constants import OVERLAY_COLORS
from src.dashboard.data_loaders import export_report_csv, load_scenes
from src.dashboard.navigation import NAV_ITEMS, get_active_page, switch_to

LEGEND_ITEMS = [
    ("no_damage", "No damage"),
    ("minor_damage", "Minor"),
    ("major_damage", "Major"),
    ("destroyed", "Destroyed"),
    ("review_required", "Review required"),
]

MATERIAL_ICONS = {
    "dashboard": ":material/dashboard:",
    "map": ":material/map:",
    "analytics": ":material/analytics:",
}


def _init_session_state() -> None:
    if "selected_scene_id" not in st.session_state:
        st.session_state.selected_scene_id = "pinery-bushfire_00000000"
    if "show_overlays" not in st.session_state:
        st.session_state.show_overlays = True
    if "overlay_opacity" not in st.session_state:
        st.session_state.overlay_opacity = 0.45


def render_sidebar_extras() -> str:
    _init_session_state()
    active = get_active_page()
    scenes = load_scenes()
    scene_ids = [s["scene_id"] for s in scenes]
    if st.session_state.selected_scene_id not in scene_ids and scene_ids:
        st.session_state.selected_scene_id = scene_ids[0]

    st.sidebar.markdown(
        '<p class="ds-nav-title">Navigation</p><p class="ds-nav-sub">Analysis Controls</p>',
        unsafe_allow_html=True,
    )

    for page_id, label, _icon_key in NAV_ITEMS:
        is_active = page_id == active
        if st.sidebar.button(
            label,
            key=f"nav_{page_id}",
            icon=MATERIAL_ICONS.get(_icon_key, ":material/circle:"),
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            switch_to(page_id)

    st.sidebar.markdown("---")

    st.sidebar.markdown('<span class="ds-label-caps">Current Scene</span>', unsafe_allow_html=True)
    selected = st.sidebar.selectbox(
        "Current scene",
        scene_ids,
        index=scene_ids.index(st.session_state.selected_scene_id),
        label_visibility="collapsed",
        key="sidebar_scene_select",
    )
    st.session_state.selected_scene_id = selected
    st.sidebar.markdown(
        f'<div class="ds-scene-box"><span class="ds-scene-id">{selected}</span></div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown('<span class="ds-label-caps">Damage Legend</span>', unsafe_allow_html=True)
    for key, leg_label in LEGEND_ITEMS:
        color = OVERLAY_COLORS.get(key, "#9AA8BC")
        st.sidebar.markdown(
            f'<div class="ds-legend-row">'
            f'<span class="ds-legend-dot" style="background:{color}"></span>{leg_label}</div>',
            unsafe_allow_html=True,
        )

    with st.sidebar.expander("View options", expanded=False):
        st.session_state.show_overlays = st.checkbox("Show damage overlays", value=st.session_state.show_overlays)
        st.session_state.overlay_opacity = st.slider("Overlay opacity", 0.1, 0.9, st.session_state.overlay_opacity, 0.05)

    st.sidebar.download_button(
        "Export Report",
        data=export_report_csv(selected),
        file_name=f"disastersight_{selected}_report.csv",
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.page_link(
        "https://github.com/matthewchungkaishing/DisasterSight",
        label="Documentation",
        icon=":material/description:",
    )
    st.sidebar.page_link(
        "https://github.com/matthewchungkaishing/DisasterSight/issues",
        label="Support",
        icon=":material/help:",
    )

    return selected
