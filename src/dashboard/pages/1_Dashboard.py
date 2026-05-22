from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import building_table, metric_card, severity_bars, shell, sidebar
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

st.markdown(f"## Scene Explorer — {disaster_type}")

cols = st.columns(4)
with cols[0]:
    metric_card.render("Total buildings", str(total))
with cols[1]:
    metric_card.render("Demo Priority Score", str(priority), sub="Illustrative triage metric")
with cols[2]:
    metric_card.render("Flagged for Review", str(review_count))
with cols[3]:
    metric_card.render_dominant_class(class_counts)

if predictions:
    avg_conf = sum(float(p.get("confidence", 0)) for p in predictions) / len(predictions)
    st.caption(f"Mean model confidence: {avg_conf * 100:.0f}%")

pre_path = resolve_image_path(scene.get("pre_image_path", ""))
post_path = resolve_image_path(scene.get("post_image_path", ""))
pre_img = load_display_image(pre_path, "Pre-disaster (demo)")
post_img = load_display_image(post_path, "Post-disaster (demo)")

if st.session_state.get("show_overlays", True):
    post_img = draw_demo_overlays(
        post_img,
        predictions,
        opacity=st.session_state.get("overlay_opacity", 0.45),
    )

img_cols = st.columns(2)
with img_cols[0]:
    st.markdown("**Pre-disaster**")
    st.image(pre_img, use_container_width=True)
with img_cols[1]:
    st.markdown("**Post-disaster (Inference)**")
    st.image(post_img, use_container_width=True)

bottom = st.columns(2)
with bottom[0]:
    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    severity_bars.render(class_counts, total)
    st.markdown("</div>", unsafe_allow_html=True)
with bottom[1]:
    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    building_table.render(predictions)
    st.markdown("</div>", unsafe_allow_html=True)

shell.render_footer(show_hitl=False)
