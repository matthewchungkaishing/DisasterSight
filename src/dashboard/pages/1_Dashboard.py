from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import building_table, metric_card, scene_explorer, severity_bars, shell, sidebar
from src.dashboard.data_loaders import (
    get_scene_by_id,
    get_zone_summary_for_scene,
    load_predictions,
)
import streamlit as st

from src.dashboard.navigation import set_active_page

set_active_page("dashboard")
shell.render_topbar("default")
scene_id = sidebar.render_sidebar_extras()

scene = get_scene_by_id(scene_id) or {}
summary = get_zone_summary_for_scene(scene_id)
predictions = load_predictions(scene_id)
class_counts = summary.get("class_counts", {})
total = summary.get("total_buildings", 0)
review_count = summary.get("review_flag_count", 0)
priority = summary.get("priority_score", 0)
disaster_type = scene.get("disaster_type", "wildfire").title()

avg_conf = 0.0
if predictions:
    avg_conf = sum(float(p.get("confidence", 0)) for p in predictions) / len(predictions)

metric_card.render_metrics_row(total, priority, review_count, class_counts)

scene_explorer.render(
    scene,
    disaster_type,
    predictions,
    avg_conf * 100,
    st.session_state.get("show_overlays", True),
    st.session_state.get("overlay_opacity", 0.45),
)

st.markdown('<div class="ds-bottom-grid">', unsafe_allow_html=True)
col_l, col_r = st.columns([1, 2])
with col_l:
    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    severity_bars.render(class_counts, total)
    st.markdown("</div>", unsafe_allow_html=True)
with col_r:
    st.markdown('<div class="ds-panel" style="padding:0">', unsafe_allow_html=True)
    building_table.render(predictions, scene_id)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

shell.render_footer(show_hitl=False)
