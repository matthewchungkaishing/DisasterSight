from __future__ import annotations

import streamlit as st

from src.dashboard.navigation import focus_scene
from src.dashboard.priority import priority_css_class
from src.dashboard.styles import icon


def render_table(
    summaries: list[dict],
    filter_mode: str = "All",
    sort_by: str = "Priority Score",
    page: int = 0,
    page_size: int = 5,
) -> list[dict]:
    """Render priority table; returns visible rows for action buttons."""
    rows = list(summaries)
    if filter_mode == "Review Required":
        rows = [r for r in rows if r.get("review_flag_count", 0) > 0]
    elif filter_mode == "Test":
        rows = [r for r in rows if r.get("split") == "test"]

    if sort_by == "Review count":
        rows.sort(key=lambda x: x.get("review_flag_count", 0), reverse=True)
    elif sort_by == "Destroyed %":
        rows.sort(key=lambda x: x.get("destroyed_share", 0), reverse=True)
    else:
        rows.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    total = len(rows)
    start = page * page_size
    page_rows = rows[start : start + page_size]

    body = ""
    for rank, row in enumerate(page_rows, start=start + 1):
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
        body += f"""
        <tr>
            <td>{rank_html}</td>
            <td class="mono">{sid}</td>
            <td>{row.get("disaster_name", "")}</td>
            <td class="mono {pcls}">{score}</td>
            <td class="mono muted">{row.get("destroyed_share", 0) * 100:.1f}</td>
            <td class="mono muted">{row.get("major_damage_share", 0) * 100:.1f}</td>
            <td class="mono muted">{row.get("damage_density", 0) * 100:.1f}</td>
            <td>{status}</td>
            <td class="right"><span class="action-btn">Inspect</span></td>
        </tr>
        """

    end = min(start + page_size, total)
    st.markdown(
        f"""
        <div class="ds-table-wrap">
            <table class="ds-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Scene ID</th>
                        <th>Disaster Name</th>
                        <th>Priority Score</th>
                        <th>Destroyed %</th>
                        <th>Major %</th>
                        <th>Damage Density</th>
                        <th>Status</th>
                        <th class="right">Actions</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </div>
        <div class="ds-footer-bar" style="margin-top:0.75rem;border:none;padding:0">
            <span>Showing {start + 1}–{end} of {total} scenes</span>
            <span>&lt; Prev &nbsp; Next &gt;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if page_rows:
        st.markdown('<div class="ds-action-row">', unsafe_allow_html=True)
        cols = st.columns(len(page_rows))
        for idx, row in enumerate(page_rows):
            sid = row.get("scene_id", "")
            with cols[idx]:
                if st.button(f"Inspect {sid}", key=f"inspect_{sid}_{page}", use_container_width=True):
                    focus_scene(sid, "dashboard")
        st.markdown("</div>", unsafe_allow_html=True)

    return page_rows
