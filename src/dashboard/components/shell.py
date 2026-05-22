from __future__ import annotations

import streamlit as st

HEADER_VARIANTS = {
    "default": "Responsible AI Active: Predictions require human validation",
    "analytics": "Model Review & Ethical Limitations Protocol Active",
}


def render_header(variant: str = "default") -> None:
    pill_text = HEADER_VARIANTS.get(variant, HEADER_VARIANTS["default"])
    pill_class = "ds-pill ds-pill-info"
    st.markdown(
        f"""
        <div class="ds-header">
            <div class="ds-header-left">
                <span class="ds-wordmark">DisasterSight</span>
                <span class="{pill_class}">⚠ {pill_text}</span>
            </div>
            <div class="ds-header-actions">
                <span class="ds-icon-btn" title="Notifications">🔔</span>
                <span class="ds-icon-btn" title="Settings">⚙</span>
                <span class="ds-ready">✓ Ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_heading(title: str, subtitle: str = "") -> None:
    sub = f'<p class="ds-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<h1 class="ds-page-title">{title}</h1>{sub}', unsafe_allow_html=True)


def render_footer(show_hitl: bool = False) -> None:
    hitl = ""
    if show_hitl:
        hitl = '<div class="ds-hitl-badge">👤 HUMAN-IN-THE-LOOP REQUIRED FOR ALL TRIAGE DECISIONS</div>'
    st.markdown(
        f"""
        <div class="ds-footer">
            {hitl}
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;align-items:center">
                <span><strong style="color:#9aa8bc">DisasterSight</strong> · v1.0.0-mvp · Decision Support Prototype · Academic Use Only</span>
                <span>
                    <a href="#" class="ds-link" style="margin-left:0.75rem;color:#6b7a90!important">Privacy Policy</a>
                    <a href="#" class="ds-link" style="margin-left:0.75rem;color:#6b7a90!important">Ethical AI Framework</a>
                    <a href="#" class="ds-link" style="margin-left:0.75rem;color:#6b7a90!important">Terms of Service</a>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
