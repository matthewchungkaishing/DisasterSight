"""Sidebar component — navigation, scene selector, overlay controls, and export."""

from __future__ import annotations

import streamlit as st

from src.dashboard.data_loaders import (
    clear_dashboard_caches,
    export_report_csv,
    load_scene_ids,
)
from src.dashboard.navigation import NAV_ITEMS, get_active_page, switch_to

_MATERIAL_ICONS: dict[str, str] = {
    "dashboard": ":material/dashboard:",
    "map": ":material/map:",
    "analytics": ":material/analytics:",
}

_DEFAULT_SCENE = ""


def _init_session_state() -> None:
    st.session_state.setdefault("selected_scene_id", _DEFAULT_SCENE)
    st.session_state.setdefault("show_overlays", True)
    st.session_state.setdefault("overlay_opacity", 0.45)


def render_sidebar_extras() -> str:
    """Render the full sidebar and return the selected scene ID."""
    _init_session_state()
    active = get_active_page()
    scenes = load_scene_ids()
    if st.session_state.selected_scene_id not in scenes and scenes:
        st.session_state.selected_scene_id = scenes[0]
    if not scenes:
        st.sidebar.warning("No scenes found. Generate a scene manifest under data/processed/.")
        return ""

    _render_navigation(active)
    selected = _render_scene_selector(scenes)
    _render_overlay_controls()
    _render_actions()
    _render_export(selected)
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
    if not scene_ids:
        return ""
    current = st.session_state.selected_scene_id
    index = scene_ids.index(current) if current in scene_ids else 0
    selected: str = st.sidebar.selectbox(
        "Current scene",
        scene_ids,
        index=index,
        label_visibility="collapsed",
        key="sidebar_scene_select",
    )
    st.session_state.selected_scene_id = selected
    st.sidebar.markdown("---")
    return selected


def _render_overlay_controls() -> None:
    st.sidebar.markdown(
        '<span class="ds-label-caps">Overlay Controls</span>',
        unsafe_allow_html=True,
    )
    st.session_state.show_overlays = st.sidebar.toggle(
        "Show model overlay",
        value=st.session_state.show_overlays,
        help="Draw cached model predictions over the post-disaster image.",
    )
    st.session_state.overlay_opacity = st.sidebar.slider(
        "Overlay opacity",
        0.1,
        0.9,
        st.session_state.overlay_opacity,
        0.05,
        disabled=not st.session_state.show_overlays,
    )
    st.sidebar.markdown("---")


def _render_actions() -> None:
    if st.sidebar.button(
        "Refresh cached artifacts",
        icon=":material/refresh:",
        use_container_width=True,
        key="sidebar_refresh",
    ):
        clear_dashboard_caches()
        st.rerun()


def _render_export(scene_id: str) -> None:
    st.sidebar.download_button(
        "Export Report",
        data=export_report_csv(scene_id),
        file_name=f"disastersight_{scene_id}_report.csv",
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    )
