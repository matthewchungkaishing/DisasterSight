"""Map Explorer page header with compact Responsible AI notice."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import shell
from src.dashboard.components.map_explorer.models import HEADER_COLUMN_WEIGHTS

_RESPONSIBLE_AI_HTML = """
<div class="ds-banner ds-banner--compact">
    <strong>Responsible AI Notice</strong>
    Priority scores are generated via algorithmic analysis of preliminary satellite imagery
    and are subject to latency and occlusion errors. Human verification is required prior
    to resource deployment.
</div>
"""


def render_header() -> None:
    """Render page title (left) and compact Responsible AI notice (right)."""
    title_col, notice_col = st.columns(HEADER_COLUMN_WEIGHTS, gap="medium")
    with title_col:
        shell.render_page_heading("Priority ranking")
    with notice_col:
        st.markdown(_RESPONSIBLE_AI_HTML, unsafe_allow_html=True)
