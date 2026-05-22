from __future__ import annotations

import streamlit as st

from src.common.constants import OVERLAY_COLORS
from src.dashboard.data_loaders import export_report_csv, load_scenes


LEGEND_ITEMS = [
    ("no_damage", "No damage"),
    ("minor_damage", "Minor"),
    ("major_damage", "Major"),
    ("destroyed", "Destroyed"),
    ("review_required", "Review required"),
]


def _init_session_state() -> None:
    if "selected_scene_id" not in st.session_state:
        st.session_state.selected_scene_id = "pinery-bushfire_00000000"
    if "show_overlays" not in st.session_state:
        st.session_state.show_overlays = True
    if "overlay_opacity" not in st.session_state:
        st.session_state.overlay_opacity = 0.45


def render_sidebar_extras() -> str:
    """Scene selector, legend, and export in sidebar. Returns selected scene_id."""
    _init_session_state()
    scenes = load_scenes()
    scene_ids = [s["scene_id"] for s in scenes]
    if st.session_state.selected_scene_id not in scene_ids and scene_ids:
        st.session_state.selected_scene_id = scene_ids[0]

    st.sidebar.markdown("### Navigation")
    st.sidebar.caption("Analysis Controls")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current scene**")
    selected = st.sidebar.selectbox(
        "Scene",
        scene_ids,
        index=scene_ids.index(st.session_state.selected_scene_id),
        label_visibility="collapsed",
        key="sidebar_scene_select",
    )
    st.session_state.selected_scene_id = selected
    st.sidebar.markdown(
        f'<span class="ds-scene-id">{selected}</span>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("**Damage legend**")
    for key, label in LEGEND_ITEMS:
        color = OVERLAY_COLORS.get(key, "#9AA8BC")
        st.sidebar.markdown(
            f'<div class="ds-legend-item">'
            f'<span class="ds-legend-swatch" style="background:{color}"></span>{label}</div>',
            unsafe_allow_html=True,
        )

    st.session_state.show_overlays = st.sidebar.checkbox(
        "Show damage overlays",
        value=st.session_state.show_overlays,
    )
    st.session_state.overlay_opacity = st.sidebar.slider(
        "Overlay opacity",
        0.1,
        0.9,
        st.session_state.overlay_opacity,
        0.05,
    )

    csv_data = export_report_csv(selected)
    st.sidebar.download_button(
        "Export Report",
        data=csv_data,
        file_name=f"disastersight_{selected}_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("[Documentation](https://github.com/matthewchungkaishing/DisasterSight)")
    st.sidebar.markdown("[Support](https://github.com/matthewchungkaishing/DisasterSight/issues)")

    return selected
