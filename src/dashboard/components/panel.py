from __future__ import annotations

import streamlit as st


def open_panel(title: str = "", subtitle: str = "", extra_class: str = "") -> None:
    """Open a styled panel; pair with close_panel() after content."""
    title_html = f'<div class="ds-panel-title">{title}</div>' if title else ""
    sub_html = f'<div class="ds-panel-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="ds-panel {extra_class}">{title_html}{sub_html}',
        unsafe_allow_html=True,
    )


def close_panel() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
