"""Dashboard page — scene-level triage overview."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import (
    building_table,
    scene_explorer,
    severity_bars,
    shell,
    sidebar,
)
from src.dashboard.components.dashboard_layout import (
    HERO_COLUMN_WEIGHTS,
    TABLE_ROW_COLUMN_WEIGHTS,
    render_section_marker,
)
from src.dashboard.components.metrics import render_scene_metrics_quadrant
from src.dashboard.data_loaders import (
    get_scene_by_id,
    get_zone_summary_for_scene,
    load_predictions,
    resolve_selected_scene_id,
)
from src.dashboard.navigation import set_active_page

set_active_page("dashboard")
shell.render_topbar()

st.session_state.setdefault("selected_scene_id", "")
resolved_scene_id = resolve_selected_scene_id(st.session_state.get("selected_scene_id"))
if resolved_scene_id:
    st.session_state.selected_scene_id = resolved_scene_id

scene_id = sidebar.render_sidebar_extras()
scene = get_scene_by_id(scene_id) or {}
summary = get_zone_summary_for_scene(scene_id)
predictions = load_predictions(scene_id)
class_counts: dict[str, int] = summary.get("class_counts", {})
total: int = summary.get("total_buildings", 0)
review_count: int = summary.get("review_flag_count", 0)
priority: float = summary.get("priority_score", 0)
disaster_type = scene.get("disaster_type", "wildfire").title()

avg_conf = 0.0
if predictions:
    avg_conf = sum(float(p.get("confidence", 0)) for p in predictions) / len(predictions)

render_section_marker("hero")
hero_left, hero_right = st.columns(HERO_COLUMN_WEIGHTS, gap="small")
with hero_left:
    scene_explorer.render(
        scene,
        disaster_type,
        predictions,
        avg_conf * 100,
        st.session_state.get("show_overlays", True),
        st.session_state.get("overlay_opacity", 0.45),
    )
with hero_right:
    render_scene_metrics_quadrant(total, priority, review_count, class_counts)
    severity_bars.render(
        class_counts,
        total,
        compact=True,
        sidebar=True,
    )

render_section_marker("table")
table_col, _table_spacer = st.columns(TABLE_ROW_COLUMN_WEIGHTS, gap="small")
with table_col:
    building_table.render(predictions, scene_id, compact=True)

shell.render_footer(show_hitl=False)
