"""KPI metric cards row component."""

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
    """Render the top-level KPI row: total buildings, priority, review count, dominant class."""
    dominant = ""
    if class_counts:
        dom_key = max(class_counts, key=lambda k: class_counts[k])
        dominant = f'<div style="margin-top:0.5rem">{render_html(dom_key)}</div>'

    trending = icon("trending_up", size=22)
    cards = [
        f'<div class="ds-metric-card">'
        f'<span class="ds-metric-label">Total buildings</span>'
        f'<div class="ds-metric-value">{total}</div></div>',
        f'<div class="ds-metric-card">'
        f'<span class="ds-metric-label">Demo Priority Score</span>'
        f'<div class="ds-metric-value error">{int(priority)} {trending}'
        f"</div></div>",
        f'<div class="ds-metric-card">'
        f'<span class="ds-metric-label">Flagged for Review</span>'
        f'<div class="ds-metric-value secondary">{review_count}'
        f"</div></div>",
        f'<div class="ds-metric-card">'
        f'<span class="ds-metric-label">Dominant Class</span>'
        f"{dominant}</div>",
    ]
    html = "".join(cards)
    st.markdown(f'<div class="ds-metrics-grid">{html}</div>', unsafe_allow_html=True)
