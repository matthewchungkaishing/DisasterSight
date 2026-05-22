"""App shell component — top bar, page heading, and footer."""

from __future__ import annotations

import streamlit as st

from src.dashboard.styles import icon

_HEADER_VARIANTS: dict[str, str] = {
    "default": "Responsible AI Active: Predictions require human validation",
    "analytics": "Model Review & Ethical Limitations Protocol Active",
}


def render_topbar(variant: str = "default") -> None:
    """Render the app-wide top bar with the responsible-AI pill."""
    pill_text = _HEADER_VARIANTS.get(variant, _HEADER_VARIANTS["default"])
    st.markdown(
        f'<div class="ds-topbar">'
        f'<div class="ds-topbar-left">'
        f'<span class="ds-wordmark">DisasterSight</span>'
        f'<span class="ds-ai-pill">{icon("warning", size=16)} {pill_text}</span></div>'
        f'<div class="ds-topbar-actions">'
        f'<span class="ds-icon-btn">{icon("notifications")}</span>'
        f'<span class="ds-icon-btn">{icon("settings")}</span>'
        f'<span class="ds-ready-btn">Ready</span></div></div>',
        unsafe_allow_html=True,
    )


def render_page_heading(title: str, subtitle: str = "") -> None:
    """Render the page title and optional subtitle."""
    sub = (
        f'<p class="ds-page-subtitle" style="color:#c2c6d6;font-size:0.9rem;'
        f'margin:0 0 1rem">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f'<h1 style="font-size:1.75rem;font-weight:600;color:#dee3ea;'
        f'margin:0 0 0.25rem">{title}</h1>{sub}',
        unsafe_allow_html=True,
    )


def render_footer(show_hitl: bool = False) -> None:
    """Render the page footer with optional HITL banner."""
    hitl = ""
    if show_hitl:
        hitl = '<div class="ds-hitl">HUMAN-IN-THE-LOOP REQUIRED FOR ALL TRIAGE DECISIONS</div>'
    st.markdown(
        f"{hitl}"
        f'<div class="ds-footer-bar">'
        f"<span>v1.0.0-mvp | DisasterSight Decision Support Prototype | Academic Use Only</span>"
        f"<span>"
        f'<a href="#">Privacy Policy</a>'
        f'<a href="#">Ethical AI Framework</a>'
        f'<a href="#">Terms of Service</a>'
        f"</span></div>",
        unsafe_allow_html=True,
    )


render_header = render_topbar
