from __future__ import annotations

import streamlit as st

from src.dashboard.priority import priority_css_class


def render_table(
    summaries: list[dict],
    filter_mode: str = "All",
    sort_by: str = "Priority Score",
    page: int = 0,
    page_size: int = 5,
) -> None:
    """Priority ranking table as styled HTML."""
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
        if review > 0:
            status_html = '<span class="ds-status-pill ds-status-review">Review</span>'
        elif split == "test":
            status_html = '<span class="ds-status-pill ds-status-test">Test</span>'
        else:
            status_html = '<span class="ds-status-verified">Verified</span>'
        rank_cls = "ds-rank-badge top" if rank == 1 else "ds-rank-badge"
        pcls = priority_css_class(float(score))
        sid = row.get("scene_id", "")
        body += f"""
        <tr>
            <td><span class="{rank_cls}">{rank}</span></td>
            <td class="mono">{sid}</td>
            <td>{row.get("disaster_name", "")}</td>
            <td class="{pcls}">{score}</td>
            <td>{row.get("destroyed_share", 0) * 100:.1f}</td>
            <td>{row.get("major_damage_share", 0) * 100:.1f}</td>
            <td>{row.get("damage_density", 0) * 100:.1f}</td>
            <td>{status_html}</td>
            <td><a href="#" class="action-link">Inspect</a></td>
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
                        <th>Disaster name</th>
                        <th>Priority score</th>
                        <th>Destroyed %</th>
                        <th>Major %</th>
                        <th>Damage density</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </div>
        <div class="ds-table-footer">
            <span>Showing {start + 1}–{end} of {total} scenes</span>
            <span>&lt; Prev &nbsp; Next &gt;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
