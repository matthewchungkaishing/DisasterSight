from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.priority import priority_css_class


def render_table(
    summaries: list[dict],
    filter_mode: str = "All",
    sort_by: str = "Priority Score",
    page: int = 0,
    page_size: int = 5,
) -> None:
    """Priority ranking table."""
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

    table_rows = []
    for rank, row in enumerate(page_rows, start=start + 1):
        score = row.get("priority_score", 0)
        review = row.get("review_flag_count", 0)
        status = "Review" if review > 0 else ("Test" if row.get("split") == "test" else "Verified")
        table_rows.append(
            {
                "Rank": rank,
                "Scene ID": row.get("scene_id", ""),
                "Disaster Name": row.get("disaster_name", ""),
                "Priority Score": score,
                "Destroyed %": f"{row.get('destroyed_share', 0) * 100:.1f}",
                "Major %": f"{row.get('major_damage_share', 0) * 100:.1f}",
                "Damage Density": f"{row.get('damage_density', 0) * 100:.1f}",
                "Status": status,
            }
        )

    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    end = min(start + page_size, total)
    st.caption(f"Showing {start + 1}–{end} of {total} scenes")
