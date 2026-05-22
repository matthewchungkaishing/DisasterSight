from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.components import confusion_matrix, metric_card, shell, sidebar
from src.dashboard.components.confusion_matrix import confusion_matrix_csv
from src.dashboard.data_loaders import failure_case_images, load_metrics
from src.dashboard.styles import inject_theme

inject_theme()
shell.render_header("analytics")
sidebar.render_sidebar_extras()

metrics = load_metrics()
matrix = metrics.get("confusion_matrix")
labels = metrics.get("confusion_labels", [])

st.markdown("## Model Evaluation & Ethical Constraints")
st.caption(
    "Overview of prediction performance metrics and documented failure modes "
    "for the baseline paired-image classifier (xBD subset, cached inference)."
)

mcols = st.columns(4)
with mcols[0]:
    delta = metrics.get("macro_f1_delta", 0)
    sub = f'<span style="color:#4CAF50">+{delta:.2f}</span>' if delta else ""
    metric_card.render("Macro F1", f"{metrics.get('macro_f1', 0):.3f}", sub=sub)
with mcols[1]:
    metric_card.render("Precision", f"{metrics.get('precision_macro', 0):.3f}", sub=metrics.get("precision_label", ""))
with mcols[2]:
    delta = metrics.get("recall_delta", 0)
    sub = f'<span style="color:#FF7043">{delta:.2f}</span>' if delta else ""
    metric_card.render("Recall", f"{metrics.get('recall_macro', 0):.3f}", sub=sub)
with mcols[3]:
    metric_card.render("Held-out Events", str(metrics.get("held_out_events", 0)), sub="Global")

left, right = st.columns([3, 2])
with left:
    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.markdown("#### Normalized Confusion Matrix")
    with header_cols[1]:
        if matrix and labels:
            csv_data = confusion_matrix_csv(matrix, labels)
            st.download_button("CSV", csv_data, "confusion_matrix.csv", mime="text/csv")
    confusion_matrix.render(matrix, labels)
    patches = metrics.get("validation_patches", 0)
    st.caption(
        f"Data normalized over {patches:,} validation patches. "
        "Notable confusion observed between 'Minor' and 'Major' damage classes."
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    st.markdown("#### Known Limitations (MVP)")
    st.markdown(
        """
        - **Historical Data Bias:** Model trained on xBD events (2018–2022). May not
          generalize to novel building types or disaster contexts.
        - **Polygon Precision:** MVP uses dataset bounding boxes rather than instance
          segmentation; area estimates carry geometric uncertainty.
        - **Illustrative Priority Scores:** Triage ranking reflects damage density shares,
          not population, infrastructure criticality, or access routes.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ds-panel">', unsafe_allow_html=True)
    st.markdown("#### Documented Failure Cases")
    failures = failure_case_images()
    if failures:
        fcols = st.columns(2)
        for idx, path in enumerate(failures[:4]):
            with fcols[idx % 2]:
                st.image(str(path), caption=path.stem.replace("_", " ").title())
    else:
        placeholders = [
            ("Cloud Shadow False Pos.", "#1a2838"),
            ("Canopy Occlusion", "#1e3028"),
            ("Arid Terrain Confusion", "#2a2418"),
            ("View Full Catalog", "#161b22"),
        ]
        prow = st.columns(2)
        for idx, (title, color) in enumerate(placeholders):
            with prow[idx % 2]:
                st.markdown(
                    f'<div style="background:{color};height:100px;border-radius:8px;'
                    f'border:1px solid #2d3a4f;display:flex;align-items:center;'
                    f'justify-content:center;color:#9aa8bc;font-size:0.8rem">{title}</div>',
                    unsafe_allow_html=True,
                )
        with st.expander("View Full Catalog (42 items)"):
            st.write("Qualitative failure cases will be added by the evaluation lead under `artifacts/figures/failures/`.")
    st.markdown("</div>", unsafe_allow_html=True)

shell.render_footer(show_hitl=True)
