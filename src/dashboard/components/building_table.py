from __future__ import annotations

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import normalize_label
from src.dashboard.navigation import focus_scene


def render(predictions: list[dict], scene_id: str, limit: int = 10) -> None:
    st.markdown(
        '<div class="ds-panel-head bordered">Top buildings by severity</div>',
        unsafe_allow_html=True,
    )
    if not predictions:
        st.markdown('<p class="muted" style="color:#c2c6d6">No predictions for this scene.</p>', unsafe_allow_html=True)
        return

    severity_order = {"destroyed": 0, "major_damage": 1, "minor_damage": 2, "no_damage": 3}

    def sort_key(p: dict) -> tuple:
        label = normalize_label(p.get("predicted_label", ""))
        return (severity_order.get(label, 9), -float(p.get("confidence", 0)))

    sorted_preds = sorted(predictions, key=sort_key)[:limit]
    body = ""
    for pred in sorted_preds:
        label = pred.get("predicted_label", "")
        if pred.get("needs_review"):
            label = "review_required"
        conf = float(pred.get("confidence", 0))
        conf_cls = "error-text" if pred.get("needs_review") else "muted"
        action = "Review" if pred.get("needs_review") else "View"
        bid = pred.get("building_id", "")
        body += f"""
        <tr>
            <td class="mono">{bid}</td>
            <td>{render_html(label)}</td>
            <td class="mono {conf_cls}">{conf * 100:.1f}%</td>
            <td class="right"><span class="action-btn">{action}</span></td>
        </tr>
        """

    st.markdown(
        f"""
        <div class="ds-table-wrap">
            <table class="ds-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Predicted Class</th>
                        <th>Confidence</th>
                        <th class="right">Action</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ds-action-row">', unsafe_allow_html=True)
    cols = st.columns(min(len(sorted_preds), 4))
    for idx, pred in enumerate(sorted_preds[:4]):
        bid = pred.get("building_id", "")
        action = "Review" if pred.get("needs_review") else "View"
        with cols[idx % len(cols)]:
            if st.button(f"{action} {bid}", key=f"bld_{bid}_{scene_id}", use_container_width=True):
                focus_scene(scene_id, "dashboard")
    st.markdown("</div>", unsafe_allow_html=True)
