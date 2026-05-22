"""Analytics page — model evaluation, limitations, and failure cases."""

from __future__ import annotations

import streamlit as st

from src.dashboard.artifact_resolver import resolve_failure_case_images
from src.dashboard.components import confusion_matrix, shell, sidebar
from src.dashboard.components.confusion_matrix import confusion_matrix_csv
from src.dashboard.data_loaders import load_metrics
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


def _delta_html(value: float, *, positive_color: str = "#4caf50") -> str:
    if abs(value) < 1e-9:
        return ""
    sign = "+" if value > 0 else ""
    color = positive_color if value >= 0 else "#6b7a90"
    return f'<span style="font-size:0.75rem;color:{color}">{sign}{value:.2f}</span>'


delta_f1 = float(metrics.get("macro_f1_delta", 0))
delta_rec = float(metrics.get("recall_delta", 0))
eval_samples = int(metrics.get("validation_patches", 0))
held_out_events = int(metrics.get("held_out_events", 0))
fourth_card_label = "Held-out Events" if held_out_events > 0 else "Eval Samples"
fourth_card_value = held_out_events if held_out_events > 0 else eval_samples

metrics_html = (
    f'<div class="ds-metric-card"><span class="ds-metric-label">Macro F1</span>'
    f'<div class="ds-metric-value">{metrics.get("macro_f1", 0):.3f} '
    f"{_delta_html(delta_f1)}</div></div>"
    f'<div class="ds-metric-card"><span class="ds-metric-label">Precision</span>'
    f'<div class="ds-metric-value">{metrics.get("precision_macro", 0):.3f} '
    f'<span style="font-size:0.75rem;color:#6b7a90">'
    f"{metrics.get('precision_label', 'Live')}</span></div></div>"
    f'<div class="ds-metric-card"><span class="ds-metric-label">Recall</span>'
    f'<div class="ds-metric-value error">{metrics.get("recall_macro", 0):.3f} '
    f"{_delta_html(delta_rec, positive_color='#6b7a90')}</div></div>"
    f'<div class="ds-metric-card"><span class="ds-metric-label">{fourth_card_label}</span>'
    f'<div class="ds-metric-value">{fourth_card_value:,} '
    f"{icon('public', size=20)}</div></div>"
)
st.markdown(f'<div class="ds-metrics-grid">{metrics_html}</div>', unsafe_allow_html=True)

left, right = st.columns([1.45, 1])
with left, st.container(border=True):
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            '<div class="ds-panel-title">Normalized Confusion Matrix</div>',
            unsafe_allow_html=True,
        )
    with hdr_r:
        if matrix and labels:
            st.download_button(
                "CSV",
                confusion_matrix_csv(matrix, labels),
                "confusion_matrix.csv",
                mime="text/csv",
            )
    confusion_matrix.render(matrix, labels)
    if eval_samples > 0:
        st.markdown(
            f'<p style="color:#6b7a90;font-size:0.78rem;margin-top:0.75rem">'
            f"Row-normalized confusion matrix from {eval_samples:,} held-out crop evaluations. "
            f"Notable confusion can occur between minor and major damage classes.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            "Run evaluate to populate real metrics and confusion matrix artifacts. "
            "Pass --save-figure to also emit the confusion-matrix PNG."
        )

with right:
    with st.container(border=True):
        st.markdown(
            '<div class="ds-panel-title">Known Limitations (MVP)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">🕐</div>
                <div>
                    <div class="ds-limitation-title">Historical Data Bias</div>
                    <div class="ds-limitation-text">Model trained on xBD events (2018-2022).
                    May not generalize to novel building types or disaster contexts.</div>
                </div>
            </div>
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">▢</div>
                <div>
                    <div class="ds-limitation-title">Polygon Precision</div>
                    <div class="ds-limitation-text">MVP uses dataset bounding boxes rather than
                    instance segmentation; area estimates carry geometric uncertainty.</div>
                </div>
            </div>
            <div class="ds-limitation-item">
                <div class="ds-limitation-icon">⊞</div>
                <div>
                    <div class="ds-limitation-title">Illustrative Priority Scores</div>
                    <div class="ds-limitation-text">Triage ranking reflects damage density shares,
                    not population, infrastructure criticality, or access routes.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown(
            '<div class="ds-panel-title">Documented Failure Cases</div>',
            unsafe_allow_html=True,
        )
        failures = resolve_failure_case_images()
        if failures:
            cols = st.columns(min(len(failures[:4]), 4))
            for col, path in zip(cols, failures[:4], strict=False):
                with col:
                    st.image(
                        str(path),
                        caption=path.stem.replace("_", " ").title(),
                        use_container_width=True,
                    )
            if len(failures) > 4:
                with st.expander(f"View all {len(failures)} failure cases"):
                    for path in failures[4:]:
                        st.image(str(path), caption=path.stem.replace("_", " ").title())
        else:
            st.info(
                "No failure-case thumbnails found. "
                "Run `make evaluate CHECKPOINT=... --save-figure` then place "
                "representative failure crops under `artifacts/figures/failures/`."
            )

shell.render_footer(show_hitl=True)
