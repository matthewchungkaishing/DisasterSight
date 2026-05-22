"""Review queue component — scenes flagged for human review."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.dashboard.navigation import focus_scene


def pending_scenes(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return summaries that have at least one review-flagged building."""
    return [s for s in summaries if s.get("review_flag_count", 0) > 0]


def count_pending_scenes(summaries: list[dict[str, Any]]) -> int:
    """Number of scenes with review-flagged buildings."""
    return len(pending_scenes(summaries))


def count_pending_buildings(summaries: list[dict[str, Any]]) -> int:
    """Total review-flagged buildings across all scenes."""
    return sum(int(s.get("review_flag_count", 0)) for s in summaries)


def review_queue_heading(summaries: list[dict[str, Any]]) -> str:
    """Build the review queue panel title from live summary data."""
    buildings = count_pending_buildings(summaries)
    if buildings <= 0:
        return "Review Queue"
    noun = "building" if buildings == 1 else "buildings"
    return f"Review Queue ({buildings} {noun} flagged)"


def render(summaries: list[dict[str, Any]], *, max_items: int = 4) -> None:
    """List scenes with review-flagged buildings."""
    pending = pending_scenes(summaries)
    if not pending:
        st.markdown(
            '<p class="ds-review-empty">No scenes flagged for review.</p>',
            unsafe_allow_html=True,
        )
        return

    for item in pending[:max_items]:
        sid = item.get("scene_id", "")
        name = item.get("disaster_name", "")
        flags = item.get("review_flag_count", 0)
        row_l, row_r = st.columns([3, 1])
        with row_l:
            st.markdown(f'<p class="ds-review-scene mono">{sid}</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="ds-review-meta">{name} · {flags} building(s) flagged</p>',
                unsafe_allow_html=True,
            )
        with row_r:
            if st.button("Start Review", key=f"review_btn_{sid}", use_container_width=True):
                focus_scene(sid, "dashboard")
