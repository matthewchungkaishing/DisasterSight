"""Building table component — top buildings by severity."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import normalize_label
from src.dashboard.navigation import focus_scene

_SEVERITY_ORDER: dict[str, int] = {
    "destroyed": 0,
    "major_damage": 1,
    "minor_damage": 2,
    "no_damage": 3,
}


def _sort_key(pred: dict[str, Any]) -> tuple[int, float]:
    label = normalize_label(pred.get("predicted_label", ""))
    return (_SEVERITY_ORDER.get(label, 9), -float(pred.get("confidence", 0)))


def render(predictions: list[dict[str, Any]], scene_id: str, limit: int = 10) -> None:
    """Render a table of the top buildings ranked by damage severity."""
    st.markdown(
        '<div class="ds-panel-head bordered">Top buildings by severity</div>',
        unsafe_allow_html=True,
    )
    if not predictions:
        st.markdown(
            '<p class="muted" style="color:#c2c6d6">No predictions for this scene.</p>',
            unsafe_allow_html=True,
        )
        return

    sorted_preds = sorted(predictions, key=_sort_key)[:limit]
    body = ""
    for pred in sorted_preds:
        label = pred.get("predicted_label", "")
        if pred.get("needs_review"):
            label = "review_required"
        conf = float(pred.get("confidence", 0))
        conf_cls = "error-text" if pred.get("needs_review") else "muted"
        action = "Review" if pred.get("needs_review") else "View"
        bid = pred.get("building_id", "")
        body += (
            f"<tr>"
            f'<td class="mono">{bid}</td>'
            f"<td>{render_html(label)}</td>"
            f'<td class="mono {conf_cls}">{conf * 100:.1f}%</td>'
            f'<td class="right"><span class="action-btn">{action}</span></td>'
            f"</tr>"
        )

    st.markdown(
        f'<div class="ds-table-wrap"><table class="ds-table">'
        f"<thead><tr><th>ID</th><th>Predicted Class</th>"
        f'<th>Confidence</th><th class="right">Action</th></tr></thead>'
        f"<tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    visible = sorted_preds[:4]
    st.markdown('<div class="ds-action-row">', unsafe_allow_html=True)
    cols = st.columns(len(visible))
    for idx, pred in enumerate(visible):
        bid = pred.get("building_id", "")
        action = "Review" if pred.get("needs_review") else "View"
        with cols[idx]:
            if st.button(f"{action} {bid}", key=f"bld_{bid}_{scene_id}", use_container_width=True):
                focus_scene(scene_id, "dashboard")
    st.markdown("</div>", unsafe_allow_html=True)
