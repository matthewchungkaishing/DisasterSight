"""DisasterSight Streamlit dashboard entry-point.

Run from the repository root::

    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from src.dashboard.sidebar_state import get_sidebar_state, init_sidebar_state  # noqa: E402
from src.dashboard.styles import inject_theme  # noqa: E402

init_sidebar_state()
st.set_page_config(
    page_title="DisasterSight",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state=get_sidebar_state(),
)

inject_theme()

_DASHBOARD_DIR = Path(__file__).parent
_PAGES = [
    st.Page(
        _DASHBOARD_DIR / "pages/1_Dashboard.py",
        title="Dashboard",
        icon=":material/dashboard:",
        default=True,
    ),
    st.Page(
        _DASHBOARD_DIR / "pages/2_Map_Explorer.py",
        title="Map Explorer",
        icon=":material/map:",
    ),
    st.Page(
        _DASHBOARD_DIR / "pages/3_Analytics.py",
        title="Analytics",
        icon=":material/analytics:",
    ),
]

pg = st.navigation(_PAGES, position="hidden")
pg.run()
