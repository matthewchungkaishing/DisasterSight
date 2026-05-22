from __future__ import annotations

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import normalize_label


def render(predictions: list[dict], limit: int = 10) -> None:
    """Top buildings table with HTML badges matching Stitch design."""
    if not predictions:
        st.markdown(
            '<p style="color:#9aa8bc;font-size:0.88rem">No building predictions for this scene.</p>',
            unsafe_allow_html=True,
        )
        return

    severity_order = {"destroyed": 0, "major_damage": 1, "minor_damage": 2, "no_damage": 3}

    def sort_key(p: dict) -> tuple:
        label = normalize_label(p.get("predicted_label", ""))
        conf = float(p.get("confidence", 0))
        return (severity_order.get(label, 9), -conf)

    sorted_preds = sorted(predictions, key=sort_key)[:limit]
    rows_html = ""
    for pred in sorted_preds:
        label = pred.get("predicted_label", "")
        if pred.get("needs_review"):
            label = "review_required"
        conf = float(pred.get("confidence", 0))
        action = "Review" if pred.get("needs_review") else "View"
        bid = pred.get("building_id", "")
        rows_html += f"""
        <tr>
            <td class="mono">{bid}</td>
            <td>{render_html(label)}</td>
            <td>{conf * 100:.1f}%</td>
            <td><a href="#" class="action-link">{action}</a></td>
        </tr>
        """

    st.markdown(
        f"""
        <div class="ds-table-wrap">
            <table class="ds-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Predicted class</th>
                        <th>Confidence</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
