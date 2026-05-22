from __future__ import annotations

from pathlib import Path

import streamlit as st

DASHBOARD_DIR = Path(__file__).parent

PAGE_PATHS = {
    "dashboard": DASHBOARD_DIR / "pages/1_Dashboard.py",
    "map_explorer": DASHBOARD_DIR / "pages/2_Map_Explorer.py",
    "analytics": DASHBOARD_DIR / "pages/3_Analytics.py",
}

NAV_ITEMS = (
    ("dashboard", "Dashboard", "dashboard"),
    ("map_explorer", "Map Explorer", "map"),
    ("analytics", "Analytics", "analytics"),
)


def set_active_page(page_id: str) -> None:
    st.session_state["ds_active_page"] = page_id


def get_active_page() -> str:
    return st.session_state.get("ds_active_page", "dashboard")


def switch_to(page_id: str) -> None:
    """Navigate to a dashboard page."""
    path = PAGE_PATHS.get(page_id)
    if path:
        set_active_page(page_id)
        # Relative to app.py (src/dashboard/)
        rel = path.relative_to(DASHBOARD_DIR)
        st.switch_page(str(rel))


def focus_scene(scene_id: str, page_id: str = "dashboard") -> None:
    """Select a scene and open the target page."""
    st.session_state.selected_scene_id = scene_id
    switch_to(page_id)
