from __future__ import annotations

import streamlit as st

from src.dashboard.components.damage_badge import render_html
from src.dashboard.labels import display_label


def _card_html(label: str, value: str, sub: str = "", badge_html: str = "") -> str:
    sub_html = f'<div class="ds-metric-sub">{sub}</div>' if sub else ""
    badge_block = f'<div class="ds-dominant-badge">{badge_html}</div>' if badge_html else ""
    value_html = f'<div class="ds-metric-value">{value}</div>' if value else ""
    return f"""
    <div class="ds-metric-card">
        <div class="ds-metric-label">{label}</div>
        {value_html}
        {sub_html}
        {badge_block}
    </div>
    """


def render(label: str, value: str, sub: str = "", badge_html: str = "") -> None:
    st.markdown(_card_html(label, value, sub, badge_html), unsafe_allow_html=True)


def render_metrics_row(cards: list[tuple[str, str, str, str]]) -> None:
    """Render a row of KPI cards as one HTML grid. Each tuple: label, value, sub, badge_html."""
    inner = "".join(_card_html(l, v, s, b) for l, v, s, b in cards)
    st.markdown(f'<div class="ds-metrics-grid">{inner}</div>', unsafe_allow_html=True)


def render_dominant_class(class_counts: dict[str, int]) -> str:
    if not class_counts:
        return _card_html("Dominant class", "—", "", "")
    dominant = max(class_counts.items(), key=lambda x: x[1])[0]
    badge = render_html(dominant)
    icon = "⚠ " if dominant in ("major_damage", "destroyed") else ""
    return _card_html("Dominant class", "", f"{icon}{display_label(dominant)}", badge)
