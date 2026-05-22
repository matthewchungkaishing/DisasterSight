"""Sidebar component — navigation, scene selector, legend, and export."""

from __future__ import annotations

import streamlit as st

from src.common.constants import OVERLAY_COLORS
from src.dashboard.data_loaders import export_report_csv, load_scenes
from src.dashboard.navigation import NAV_ITEMS, get_active_page, switch_to

_LEGEND_ITEMS: list[tuple[str, str]] = [
    ("no_damage", "No damage"),
    ("minor_damage", "Minor"),
    ("major_damage", "Major"),
    ("destroyed", "Destroyed"),
    ("review_required", "Review required"),
]

_MATERIAL_ICONS: dict[str, str] = {
    "dashboard": ":material/dashboard:",
    "map": ":material/map:",
    "analytics": ":material/analytics:",
}

_DEFAULT_SCENE = "pinery-bushfire_00000000"


def _init_session_state() -> None:
    st.session_state.setdefault("selected_scene_id", _DEFAULT_SCENE)
    st.session_state.setdefault("show_overlays", True)
    st.session_state.setdefault("overlay_opacity", 0.45)


def render_sidebar_extras() -> str:
    """Render the full sidebar and return the selected scene ID."""
    _init_session_state()
    active = get_active_page()
    scenes = load_scenes()
    scene_ids = [s["scene_id"] for s in scenes]
    if st.session_state.selected_scene_id not in scene_ids and scene_ids:
        st.session_state.selected_scene_id = scene_ids[0]

    _render_navigation(active)
    selected = _render_scene_selector(scene_ids)
    _render_legend()
    _render_view_options()
    _render_export(selected)
    _render_links()
    return selected


def _render_navigation(active: str) -> None:
    st.sidebar.markdown(
        '<p class="ds-nav-title">Navigation</p><p class="ds-nav-sub">Analysis Controls</p>',
        unsafe_allow_html=True,
    )
    for page_id, label, icon_key in NAV_ITEMS:
        is_active = page_id == active
        if st.sidebar.button(
            label,
            key=f"nav_{page_id}",
            icon=_MATERIAL_ICONS.get(icon_key, ":material/circle:"),
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            switch_to(page_id)
    st.sidebar.markdown("---")


def _render_scene_selector(scene_ids: list[str]) -> str:
    st.sidebar.markdown(
        '<span class="ds-label-caps">Current Scene</span>',
        unsafe_allow_html=True,
    )
    selected: str = st.sidebar.selectbox(
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
    return selected


def _render_legend() -> None:
    st.sidebar.markdown(
        '<span class="ds-label-caps">Damage Legend</span>',
        unsafe_allow_html=True,
    )
    for key, label in _LEGEND_ITEMS:
        color = OVERLAY_COLORS.get(key, "#9AA8BC")
        st.sidebar.markdown(
            f'<div class="ds-legend-row">'
            f'<span class="ds-legend-dot" style="background:{color}"></span>{label}</div>',
            unsafe_allow_html=True,
        )


def _render_view_options() -> None:
    with st.sidebar.expander("View options", expanded=False):
        st.session_state.show_overlays = st.checkbox(
            "Show damage overlays",
            value=st.session_state.show_overlays,
        )
        st.session_state.overlay_opacity = st.slider(
            "Overlay opacity",
            0.1,
            0.9,
            st.session_state.overlay_opacity,
            0.05,
        )


def _render_export(scene_id: str) -> None:
    st.sidebar.download_button(
        "Export Report",
        data=export_report_csv(scene_id),
        file_name=f"disastersight_{scene_id}_report.csv",
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    )


def _render_links() -> None:
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
