from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import building_table, metric_card, severity_bars, shell, sidebar
from src.dashboard.components.metric_card import _card_html, render_dominant_class
from src.dashboard.data_loaders import (
    get_scene_by_id,
    get_zone_summary_for_scene,
    load_predictions,
    resolve_image_path,
)
from src.dashboard.overlays import draw_demo_overlays, load_display_image
from src.dashboard.styles import inject_theme

inject_theme()
shell.render_header("default")
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

metrics_html = (
    _card_html("Total buildings", str(total), "", "")
    + _card_html("Demo Priority Score", str(int(priority)), '<span class="ds-trend-up">↗</span>', "")
    + _card_html("Flagged for Review", str(review_count), "", "")
    + render_dominant_class(class_counts)
)
st.markdown(f'<div class="ds-metrics-grid">{metrics_html}</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        f"""
        <div class="ds-scene-panel-head">
            <span class="ds-panel-title">Scene Explorer — {disaster_type}</span>
            <span class="ds-confidence">Confidence: {avg_conf * 100:.0f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pre_path = resolve_image_path(scene.get("pre_image_path", ""))
    post_path = resolve_image_path(scene.get("post_image_path", ""))
    pre_img = load_display_image(pre_path, "Pre-disaster")
    post_img = load_display_image(post_path, "Post-disaster")
    if st.session_state.get("show_overlays", True):
        post_img = draw_demo_overlays(
            post_img,
            predictions,
            opacity=st.session_state.get("overlay_opacity", 0.45),
        )
    img_cols = st.columns(2)
    with img_cols[0]:
        st.markdown('<div class="ds-image-label">Pre-disaster</div>', unsafe_allow_html=True)
        st.image(pre_img, use_container_width=True)
    with img_cols[1]:
        st.markdown('<div class="ds-image-label">Post-disaster (Inference)</div>', unsafe_allow_html=True)
        st.image(post_img, use_container_width=True)

col_left, col_right = st.columns(2)
with col_left:
    with st.container(border=True):
        severity_bars.render(class_counts, total)
with col_right:
    with st.container(border=True):
        st.markdown('<div class="ds-panel-title">Top buildings by severity</div>', unsafe_allow_html=True)
        building_table.render(predictions)

shell.render_footer(show_hitl=False)
