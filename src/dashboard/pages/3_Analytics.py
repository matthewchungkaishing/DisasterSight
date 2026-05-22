from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import confusion_matrix, shell, sidebar
from src.dashboard.components.confusion_matrix import confusion_matrix_csv
from src.dashboard.data_loaders import failure_case_images, load_metrics
from src.dashboard.navigation import set_active_page
from src.dashboard.navigation import set_active_page
from src.dashboard.styles import icon

set_active_page("analytics")
shell.render_topbar("analytics")
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
    f'<div class="ds-metric-card"><span class="ds-metric-label">Macro F1</span>'
    f'<div class="ds-metric-value">{metrics.get("macro_f1", 0):.3f} '
    f'<span style="font-size:0.75rem;color:#4caf50">+{delta_f1:.2f}</span></div></div>'
    f'<div class="ds-metric-card"><span class="ds-metric-label">Precision</span>'
    f'<div class="ds-metric-value">{metrics.get("precision_macro", 0):.3f} '
    f'<span style="font-size:0.75rem;color:#6b7a90">— {metrics.get("precision_label", "Stbl")}</span></div></div>'
    f'<div class="ds-metric-card"><span class="ds-metric-label">Recall</span>'
    f'<div class="ds-metric-value error">{metrics.get("recall_macro", 0):.3f} '
    f'<span style="font-size:0.75rem">{delta_rec:.2f}</span></div></div>'
    f'<div class="ds-metric-card"><span class="ds-metric-label">Held-out Events</span>'
    f'<div class="ds-metric-value">{metrics.get("held_out_events", 0)} {icon("public", size=20)}</div></div>'
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
