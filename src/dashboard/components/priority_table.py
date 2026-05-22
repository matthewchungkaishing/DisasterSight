"""Priority ranking table component for Map Explorer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.components.map_explorer.models import PAGE_SIZE, TABLE_BODY_COLUMN_WEIGHTS
from src.dashboard.components.map_explorer.table_data import filter_and_sort_rows, paginate_rows
from src.dashboard.navigation import focus_scene
from src.dashboard.priority import priority_css_class
from src.dashboard.styles import icon


def render_table(
    summaries: list[dict[str, Any]],
    filter_mode: str = "All",
    sort_by: str = "Priority Score",
    page: int = 0,
    page_size: int = PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Render a priority-ranked table. Returns the visible page rows."""
    rows = filter_and_sort_rows(summaries, filter_mode, sort_by)
    page_rows, start, end, _page = paginate_rows(rows, page, page_size)
    total = len(rows)

    body = _build_table_body(page_rows, start)
    table_col, actions_col = st.columns(TABLE_BODY_COLUMN_WEIGHTS, gap="small")

    with table_col:
        st.markdown(
            f'<div class="ds-table-wrap"><table class="ds-table ds-table--priority">'
            f"<thead><tr>"
            f"<th>Rank</th><th>Scene ID</th><th>Disaster Name</th>"
            f"<th>Priority Score</th><th>Destroyed %</th><th>Major %</th>"
            f"<th>Damage Density</th><th>Status</th>"
            f'<th class="right">Actions</th></tr></thead>'
            f"<tbody>{body}</tbody></table></div>"
            f'<div class="ds-footer-bar ds-table-range">'
            f"<span>Showing {start + 1 if total else 0}-{end} of {total} scenes</span></div>",
            unsafe_allow_html=True,
        )

    with actions_col:
        st.markdown(
            '<div class="ds-table-actions" aria-hidden="true">Actions</div>', unsafe_allow_html=True
        )
        if page_rows:
            for row in page_rows:
                sid = row.get("scene_id", "")
                if st.button(
                    "Inspect",
                    key=f"inspect_{sid}_{page}",
                    use_container_width=True,
                ):
                    focus_scene(sid, "dashboard")

    return page_rows


def _build_table_body(page_rows: list[dict[str, Any]], offset: int) -> str:
    body = ""
    for rank, row in enumerate(page_rows, start=offset + 1):
        score = row.get("priority_score", 0)
        review = row.get("review_flag_count", 0)
        split = row.get("split", "")
        sid = row.get("scene_id", "")

        rank_html = (
            f'<span class="ds-rank-dot top">{rank}</span>'
            if rank == 1
            else f'<span class="ds-rank-dot">{rank}</span>'
        )
        if review > 0:
            status = f'<span class="ds-status-review">{icon("visibility", size=14)} Review</span>'
        elif split == "test":
            status = '<span class="muted">Test</span>'
        else:
            status = '<span class="muted">Verified</span>'

        pcls = priority_css_class(float(score))
        body += (
            f"<tr><td>{rank_html}</td>"
            f'<td class="mono">{sid}</td>'
            f"<td>{row.get('disaster_name', '')}</td>"
            f'<td class="mono {pcls}">{score}</td>'
            f'<td class="mono muted">{row.get("destroyed_share", 0) * 100:.1f}</td>'
            f'<td class="mono muted">{row.get("major_damage_share", 0) * 100:.1f}</td>'
            f'<td class="mono muted">{row.get("damage_density", 0) * 100:.1f}</td>'
            f"<td>{status}</td>"
            f'<td class="right muted">—</td></tr>'
        )
    return body
