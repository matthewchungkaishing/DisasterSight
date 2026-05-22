from __future__ import annotations

import streamlit as st

from src.dashboard.components.damage_badge import render_html


def render(label: str, value: str, sub: str = "", badge_html: str = "") -> None:
    """Render Stitch-style KPI metric card."""
    sub_html = f'<div class="ds-metric-sub">{sub}</div>' if sub else ""
    badge_block = f'<div style="margin-top:0.5rem">{badge_html}</div>' if badge_html else ""
    st.markdown(
        f"""
        <div class="ds-metric-card">
            <div class="ds-metric-label">{label}</div>
            <div class="ds-metric-value">{value}</div>
            {sub_html}
            {badge_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dominant_class(class_counts: dict[str, int]) -> None:
    if not class_counts:
        render("Dominant class", "—")
        return
    dominant = max(class_counts.items(), key=lambda x: x[1])[0]
    badge = render_html(dominant)
    render("Dominant class", "", badge_html=badge)
