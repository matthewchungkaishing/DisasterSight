"""Map Explorer toolbar — scene filters, sort, and pagination."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.components.map_explorer.models import (
    FILTER_OPTIONS,
    SESSION_PAGE_KEY,
    SORT_OPTIONS,
    TOOLBAR_COLUMN_WEIGHTS,
)
from src.dashboard.components.map_explorer.table_data import (
    clamp_page,
    filter_and_sort_rows,
    max_page_index,
)


def _reset_page() -> None:
    st.session_state[SESSION_PAGE_KEY] = 0


def render_toolbar(summaries: list[dict[str, Any]]) -> tuple[str, str, int]:
    """Render filter, sort, and pagination controls. Returns (filter_mode, sort_by, page)."""
    st.markdown(
        '<div class="ds-map-explorer-toolbar" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    filter_col, sort_col, page_col = st.columns(
        TOOLBAR_COLUMN_WEIGHTS,
        gap="small",
        vertical_alignment="bottom",
    )

    with filter_col:
        filter_mode = st.radio(
            "Filter scenes",
            list(FILTER_OPTIONS),
            horizontal=True,
            label_visibility="collapsed",
            key="map_explorer_filter",
            on_change=_reset_page,
        )
    with sort_col:
        label_col, select_col = st.columns([0.42, 1], gap="small", vertical_alignment="bottom")
        with label_col:
            st.markdown('<p class="ds-toolbar-label">Sort by</p>', unsafe_allow_html=True)
        with select_col:
            sort_by = st.selectbox(
                "Sort field",
                list(SORT_OPTIONS),
                label_visibility="collapsed",
                key="map_explorer_sort",
                on_change=_reset_page,
            )

    rows = filter_and_sort_rows(summaries, filter_mode, sort_by)
    total = len(rows)
    max_page = max_page_index(total)

    page = st.session_state.setdefault(SESSION_PAGE_KEY, 0)
    page = clamp_page(page, total)
    st.session_state[SESSION_PAGE_KEY] = page

    with page_col:
        prev_col, label_col, next_col = st.columns(
            [1, 1.4, 1],
            gap="small",
            vertical_alignment="center",
        )
        with prev_col:
            if st.button(
                "Prev",
                key="map_explorer_prev",
                disabled=page <= 0,
                use_container_width=True,
            ):
                st.session_state[SESSION_PAGE_KEY] = page - 1
                st.rerun()
        with label_col:
            st.markdown(
                f'<p class="ds-pagination-label">Page {page + 1} of {max_page + 1}</p>',
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button(
                "Next",
                key="map_explorer_next",
                disabled=page >= max_page,
                use_container_width=True,
            ):
                st.session_state[SESSION_PAGE_KEY] = page + 1
                st.rerun()

    return filter_mode, sort_by, page
