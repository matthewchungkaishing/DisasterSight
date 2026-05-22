from __future__ import annotations

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.styles import icon


def render_metrics_row(
    total: int,
    priority: float,
    review_count: int,
    class_counts: dict[str, int],
) -> None:
    """Stitch KPI row matching exported HTML."""
    dominant = ""
    if class_counts:
        dom_key = max(class_counts.items(), key=lambda x: x[1])[0]
        dominant = f'<div style="margin-top:0.5rem">{render_html(dom_key)}</div>'

    html = (
        f'<div class="ds-metric-card"><span class="ds-metric-label">Total buildings</span>'
        f'<div class="ds-metric-value">{total}</div></div>'
        f'<div class="ds-metric-card"><span class="ds-metric-label">Demo Priority Score</span>'
        f'<div class="ds-metric-value error">{int(priority)} {icon("trending_up", size=22)}</div></div>'
        f'<div class="ds-metric-card"><span class="ds-metric-label">Flagged for Review</span>'
        f'<div class="ds-metric-value secondary">{review_count}</div></div>'
        f'<div class="ds-metric-card"><span class="ds-metric-label">Dominant Class</span>{dominant}</div>'
    )
    st.markdown(f'<div class="ds-metrics-grid">{html}</div>', unsafe_allow_html=True)
