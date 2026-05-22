from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import display_label, normalize_label


def render(predictions: list[dict], limit: int = 10) -> None:
    """Top buildings table with styled predicted class."""
    st.markdown('<div class="ds-panel-title">Top buildings by severity</div>', unsafe_allow_html=True)
    if not predictions:
        st.info("No building predictions available for this scene.")
        return

    severity_order = {"destroyed": 0, "major_damage": 1, "minor_damage": 2, "no_damage": 3}

    def sort_key(p: dict) -> tuple:
        label = normalize_label(p.get("predicted_label", ""))
        conf = float(p.get("confidence", 0))
        return (severity_order.get(label, 9), -conf)

    sorted_preds = sorted(predictions, key=sort_key)[:limit]
    rows = []
    for pred in sorted_preds:
        label = pred.get("predicted_label", "")
        if pred.get("needs_review"):
            label = "review_required"
        conf = float(pred.get("confidence", 0))
        action = "Review" if pred.get("needs_review") else "View"
        rows.append(
            {
                "ID": pred.get("building_id", ""),
                "PREDICTED CLASS": display_label(label),
                "CONFIDENCE": f"{conf * 100:.1f}%",
                "ACTION": action,
                "_badge": render_html(label),
            }
        )

    df = pd.DataFrame(rows)
    display_df = df[["ID", "PREDICTED CLASS", "CONFIDENCE", "ACTION"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
