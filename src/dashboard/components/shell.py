"""App shell component — top bar, page heading, and footer."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def _logo_data_uri() -> str:
    """Return a data URI for the MDN logo PNG."""
    logo_path = _ASSETS_DIR / "mdn_logo.png"
    data = logo_path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_topbar() -> None:
    """Render the app-wide top bar with logo and wordmark."""
    logo_uri = _logo_data_uri()
    st.markdown(
        f'<div class="ds-topbar">'
        f'<div class="ds-topbar-left">'
        f'<span class="ds-brand-lockup">'
        f'<img class="ds-mdn-logo" src="{logo_uri}" alt="Monash DeepNeuron" />'
        f'<span class="ds-wordmark">DisasterSight</span></span></div></div>',
        unsafe_allow_html=True,
    )


def render_page_heading(title: str, subtitle: str = "") -> None:
    """Render the page title and optional subtitle."""
    sub = f'<p class="ds-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h1 class="ds-page-title">{title}</h1>{sub}',
        unsafe_allow_html=True,
    )


def render_footer(show_hitl: bool = False) -> None:
    """Render the page footer with optional review reminder."""
    hitl = ""
    if show_hitl:
        hitl = (
            '<p class="ds-footer-note">Model outputs require human review before any '
            "operational use.</p>"
        )
    st.markdown(
        f"{hitl}"
        f'<div class="ds-footer-bar">'
        f"<span>v1.0.0-mvp | DisasterSight Decision Support Prototype | Academic Use Only</span>"
        f'<span class="ds-footer-links">'
        f'<span class="ds-footer-link">Privacy Policy</span>'
        f'<span class="ds-footer-link">Ethical AI Framework</span>'
        f'<span class="ds-footer-link">Terms of Service</span>'
        f"</span></div>",
        unsafe_allow_html=True,
    )
