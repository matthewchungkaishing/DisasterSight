from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import confusion_matrix, shell, sidebar
from src.dashboard.components.confusion_matrix import confusion_matrix_csv
from src.dashboard.components.metric_card import _card_html
from src.dashboard.data_loaders import failure_case_images, load_metrics
from src.dashboard.styles import inject_theme

inject_theme()
shell.render_header("analytics")
sidebar.render_sidebar_extras()

metrics = load_metrics()
matrix = metrics.get("confusion_matrix")
labels = metrics.get("confusion_labels", [])

shell.render_page_heading(
    "Model Evaluation & Ethical Constraints",
    "Overview of prediction performance metrics and documented failure modes "
    "for the baseline paired-image classifier (xBD subset, cached inference).",
)

delta_f1 = metrics.get("macro_f1_delta", 0)
delta_rec = metrics.get("recall_delta", 0)
metrics_html = (
    _card_html("Macro F1", f"{metrics.get('macro_f1', 0):.3f}", f'<span class="ds-trend-up">+{delta_f1:.2f}</span>', "")
    + _card_html("Precision", f"{metrics.get('precision_macro', 0):.3f}", f"— {metrics.get('precision_label', 'Stbl')}", "")
    + _card_html("Recall", f"{metrics.get('recall_macro', 0):.3f}", f'<span class="ds-trend-down">{delta_rec:.2f}</span>', "")
    + _card_html("Held-out Events", str(metrics.get("held_out_events", 0)), "🌐 Global", "")
)
st.markdown(f'<div class="ds-metrics-grid">{metrics_html}</div>', unsafe_allow_html=True)

left, right = st.columns([1.45, 1])
with left:
    with st.container(border=True):
        hdr_l, hdr_r = st.columns([3, 1])
        with hdr_l:
            st.markdown('<div class="ds-panel-title">Normalized Confusion Matrix</div>', unsafe_allow_html=True)
        with hdr_r:
            if matrix and labels:
                st.download_button("CSV", confusion_matrix_csv(matrix, labels), "confusion_matrix.csv", mime="text/csv")
        confusion_matrix.render(matrix, labels)
        patches = metrics.get("validation_patches", 0)
        st.markdown(
            f'<p style="color:#6b7a90;font-size:0.78rem;margin-top:0.75rem">'
            f"Data normalized over {patches:,} validation patches. "
            f"Notable confusion between Minor and Major damage classes.</p>",
            unsafe_allow_html=True,
        )

with right:
    with st.container(border=True):
        st.markdown('<div class="ds-panel-title">Known Limitations (MVP)</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">🕐</div>
                <div>
                    <div class="ds-limitation-title">Historical Data Bias</div>
                    <div class="ds-limitation-text">Model trained on xBD events (2018–2022). May not generalize to novel building types or disaster contexts.</div>
                </div>
            </div>
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">▢</div>
                <div>
                    <div class="ds-limitation-title">Polygon Precision</div>
                    <div class="ds-limitation-text">MVP uses dataset bounding boxes rather than instance segmentation; area estimates carry geometric uncertainty.</div>
                </div>
            </div>
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">⊞</div>
                <div>
                    <div class="ds-limitation-title">Illustrative Priority Scores</div>
                    <div class="ds-limitation-text">Triage ranking reflects damage density shares, not population, infrastructure criticality, or access routes.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown('<div class="ds-panel-title">Documented Failure Cases</div>', unsafe_allow_html=True)
        failures = failure_case_images()
        if failures:
            grid = '<div class="ds-failure-grid">'
            for path in failures[:4]:
                title = path.stem.replace("_", " ").title()
                grid += f"""
                <div class="ds-failure-thumb">
                    <img src="file://{path}" alt="{title}" />
                    <div class="ds-failure-caption">{title}</div>
                </div>
                """
            grid += "</div>"
            st.markdown(grid, unsafe_allow_html=True)
        else:
            placeholders = [
                ("Cloud Shadow False Pos.", "#1a2838"),
                ("Canopy Occlusion", "#1e3028"),
                ("Arid Terrain Confusion", "#2a2418"),
                ("View Full Catalog (42 items)", "#161b22"),
            ]
            grid = '<div class="ds-failure-grid">'
            for title, color in placeholders:
                grid += f"""
                <div class="ds-failure-thumb" style="background:{color}">
                    <div class="ds-failure-caption">{title}</div>
                </div>
                """
            grid += "</div>"
            st.markdown(grid, unsafe_allow_html=True)
        with st.expander("View Full Catalog (42 items)"):
            st.caption("Add thumbnails under `artifacts/figures/failures/`.")

shell.render_footer(show_hitl=True)
