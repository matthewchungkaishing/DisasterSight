"""Map Explorer page — zone priority ranking and review queue."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components import priority_table, shell, sidebar
from src.dashboard.components.map_explorer import (
    render_bottom_panels,
    render_header,
    render_toolbar,
)
from src.dashboard.data_loaders import load_zone_summaries
from src.dashboard.navigation import set_active_page

set_active_page("map_explorer")
sidebar.render_sidebar_extras()
shell.render_topbar()

render_header()

summaries = load_zone_summaries()
filter_mode, sort_by, page = render_toolbar(summaries)

with st.container(border=True):
    priority_table.render_table(summaries, filter_mode, sort_by, page=page)

if summaries:
    render_bottom_panels(summaries, filter_mode, sort_by)

shell.render_footer(show_hitl=False)
