"""Dashboard page layout helpers - Scene Explorer-first composition."""

from __future__ import annotations

import streamlit as st

# Streamlit column weights: Scene Explorer dominates; table row aligns with left column.
HERO_COLUMN_WEIGHTS: list[float] = [7, 2]
TABLE_ROW_COLUMN_WEIGHTS: list[float] = [7, 2]


def render_section_marker(section: str) -> None:
    """Emit a zero-size marker so theme CSS can target the next row."""
    st.markdown(
        f'<div class="ds-page-section ds-page-section--{section}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
