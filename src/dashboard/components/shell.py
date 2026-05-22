from __future__ import annotations

import streamlit as st

from src.dashboard.styles import icon

HEADER_VARIANTS = {
    "default": "Responsible AI Active: Predictions require human validation",
    "analytics": "Model Review & Ethical Limitations Protocol Active",
}


def render_topbar(variant: str = "default") -> None:
    pill_text = HEADER_VARIANTS.get(variant, HEADER_VARIANTS["default"])
    st.markdown(
        f"""
        <div class="ds-topbar">
            <div class="ds-topbar-left">
                <span class="ds-wordmark">DisasterSight</span>
                <span class="ds-ai-pill">{icon("warning", size=16)} {pill_text}</span>
            </div>
            <div class="ds-topbar-actions">
                <span class="ds-icon-btn">{icon("notifications")}</span>
                <span class="ds-icon-btn">{icon("settings")}</span>
                <span class="ds-ready-btn">Ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_heading(title: str, subtitle: str = "") -> None:
    sub = f'<p class="ds-page-subtitle" style="color:#c2c6d6;font-size:0.9rem;margin:0 0 1rem">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h1 style="font-size:1.75rem;font-weight:600;color:#dee3ea;margin:0 0 0.25rem">{title}</h1>{sub}',
        unsafe_allow_html=True,
    )


def render_footer(show_hitl: bool = False) -> None:
    hitl = ""
    if show_hitl:
        hitl = '<div class="ds-hitl">HUMAN-IN-THE-LOOP REQUIRED FOR ALL TRIAGE DECISIONS</div>'
    st.markdown(
        f"""
        {hitl}
        <div class="ds-footer-bar">
            <span>v1.0.0-mvp | DisasterSight Decision Support Prototype | Academic Use Only</span>
            <span>
                <a href="#">Privacy Policy</a>
                <a href="#">Ethical AI Framework</a>
                <a href="#">Terms of Service</a>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Backwards-compatible alias
render_header = render_topbar
