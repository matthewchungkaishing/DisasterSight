"""DisasterSight Streamlit dashboard entrypoint.

Run from repository root:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.styles import inject_theme

st.set_page_config(
    page_title="DisasterSight",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

DASHBOARD_DIR = Path(__file__).parent

pages = [
    st.Page(
        DASHBOARD_DIR / "pages/1_Dashboard.py",
        title="Dashboard",
        icon=":material/dashboard:",
        default=True,
    ),
    st.Page(
        DASHBOARD_DIR / "pages/2_Map_Explorer.py",
        title="Map Explorer",
        icon=":material/map:",
    ),
    st.Page(
        DASHBOARD_DIR / "pages/3_Analytics.py",
        title="Analytics",
        icon=":material/analytics:",
    ),
]

pg = st.navigation(pages, position="hidden")
pg.run()
