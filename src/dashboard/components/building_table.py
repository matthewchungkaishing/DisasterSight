"""Building table component — top buildings by severity."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import normalize_label

_SEVERITY_ORDER: dict[str, int] = {
    "destroyed": 0,
    "major_damage": 1,
    "minor_damage": 2,
    "no_damage": 3,
}


def _sort_key(pred: dict[str, Any]) -> tuple[int, float]:
    label = normalize_label(pred.get("predicted_label", ""))
    return (_SEVERITY_ORDER.get(label, 9), -float(pred.get("confidence", 0)))


def render(predictions: list[dict[str, Any]], _scene_id: str, limit: int = 8) -> None:
    """Render a table of the top buildings ranked by damage severity."""
    if not predictions:
        st.markdown(
            '<div class="ds-panel ds-table-panel">'
            '<div class="ds-panel-head bordered">Top buildings by severity</div>'
            '<p class="muted" style="color:#c2c6d6;padding:1rem">'
            "No predictions for this scene.</p></div>",
            unsafe_allow_html=True,
        )
        return

    sorted_preds = sorted(predictions, key=_sort_key)[:limit]
    body = ""
    for pred in sorted_preds:
        label = normalize_label(pred.get("predicted_label", ""))
        badge_html = render_html(label)
        if pred.get("needs_review"):
            badge_html += ' <span class="ds-badge ds-badge-review_required">Review</span>'
        conf = float(pred.get("confidence", 0))
        conf_cls = "error-text" if pred.get("needs_review") else "muted"
        bid = pred.get("building_id", "")
        body += (
            f"<tr>"
            f'<td class="mono">{bid}</td>'
            f"<td>{badge_html}</td>"
            f'<td class="mono {conf_cls}">{conf * 100:.1f}%</td>'
            f"</tr>"
        )

    st.markdown(
        f'<div class="ds-panel ds-table-panel">'
        f'<div class="ds-panel-head bordered">Top buildings by severity</div>'
        f'<div class="ds-table-wrap"><table class="ds-table">'
        f"<thead><tr><th>ID</th><th>Predicted Class</th>"
        f"<th>Confidence</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div></div>",
        unsafe_allow_html=True,
    )
