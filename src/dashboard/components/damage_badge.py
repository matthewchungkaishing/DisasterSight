from __future__ import annotations

import streamlit as st

from src.dashboard.labels import badge_class, display_label


def render(label: str) -> None:
    """Render HTML damage severity badge."""
    css_class = badge_class(label)
    text = display_label(label)
    st.markdown(
        f'<span class="ds-badge ds-badge-{css_class}">{text}</span>',
        unsafe_allow_html=True,
    )


def render_html(label: str) -> str:
    css_class = badge_class(label)
    text = display_label(label)
    return f'<span class="ds-badge ds-badge-{css_class}">{text}</span>'
