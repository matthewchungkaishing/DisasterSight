"""Pure filter, sort, and pagination logic for Map Explorer."""

from __future__ import annotations

from typing import Any

from src.dashboard.components.map_explorer.models import PAGE_SIZE, SORT_FIELD_KEYS


def filter_and_sort_rows(
    summaries: list[dict[str, Any]],
    filter_mode: str,
    sort_by: str,
) -> list[dict[str, Any]]:
    """Return zone summaries filtered and sorted for display."""
    rows = list(summaries)
    if filter_mode == "Review Required":
        rows = [r for r in rows if r.get("review_flag_count", 0) > 0]
    elif filter_mode == "Test":
        rows = [r for r in rows if r.get("split") == "test"]

    key = SORT_FIELD_KEYS.get(sort_by, "priority_score")
    rows.sort(key=lambda row: row.get(key, 0), reverse=True)
    return rows


def clamp_page(page: int, total: int, page_size: int = PAGE_SIZE) -> int:
    """Clamp a zero-based page index to valid bounds for ``total`` rows."""
    if total <= 0:
        return 0
    max_page = (total - 1) // page_size
    return max(0, min(page, max_page))


def max_page_index(total: int, page_size: int = PAGE_SIZE) -> int:
    """Return the highest valid zero-based page index."""
    if total <= 0:
        return 0
    return (total - 1) // page_size


def paginate_rows(
    rows: list[dict[str, Any]],
    page: int,
    page_size: int = PAGE_SIZE,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Slice ``rows`` for ``page`` and return (page_rows, start, end, clamped_page)."""
    total = len(rows)
    clamped = clamp_page(page, total, page_size)
    start = clamped * page_size
    end = min(start + page_size, total)
    return rows[start:end], start, end, clamped
