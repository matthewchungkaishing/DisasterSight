"""Sidebar state helpers for Streamlit ``initial_sidebar_state``."""

from __future__ import annotations

from typing import Literal

import streamlit as st

SidebarState = Literal["auto", "expanded", "collapsed"]

SIDEBAR_STATE_KEY = "sidebar_state"
_VALID_STATES = frozenset({"expanded", "collapsed", "auto"})


def init_sidebar_state(default: str = "expanded") -> None:
    """Ensure session state has a valid sidebar state."""
    if SIDEBAR_STATE_KEY not in st.session_state:
        st.session_state[SIDEBAR_STATE_KEY] = default


def get_sidebar_state() -> SidebarState:
    """Return the sidebar state used for ``st.set_page_config``."""
    state = st.session_state.get(SIDEBAR_STATE_KEY, "expanded")
    return state if state in _VALID_STATES else "expanded"
