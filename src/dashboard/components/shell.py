from __future__ import annotations

import streamlit as st

HEADER_VARIANTS = {
    "default": "Responsible AI Active: Predictions require human validation",
    "analytics": "Model Review & Ethical Limitations Protocol Active",
}


def render_header(variant: str = "default") -> None:
    pill_text = HEADER_VARIANTS.get(variant, HEADER_VARIANTS["default"])
    pill_class = "ds-pill ds-pill-info" if variant == "analytics" else "ds-pill"
    st.markdown(
        f"""
        <div class="ds-header">
            <div class="ds-wordmark">DisasterSight</div>
            <div style="display:flex;align-items:center;gap:1rem">
                <span class="{pill_class}">⚠ {pill_text}</span>
                <span class="ds-ready">✓ Ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(show_hitl: bool = False) -> None:
    hitl = ""
    if show_hitl:
        hitl = '<div class="ds-hitl-badge">HUMAN-IN-THE-LOOP REQUIRED FOR ALL TRIAGE DECISIONS</div>'
    st.markdown(
        f"""
        <div class="ds-footer">
            {hitl}
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
                <span>v1.0.0-mvp | DisasterSight Decision Support Prototype | Academic Use Only</span>
                <span>
                    <a href="#" style="color:#6b7a90;margin-left:0.75rem">Privacy Policy</a>
                    <a href="#" style="color:#6b7a90;margin-left:0.75rem">Ethical AI Framework</a>
                    <a href="#" style="color:#6b7a90;margin-left:0.75rem">Terms of Service</a>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
