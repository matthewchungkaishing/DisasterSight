"""Map Explorer layout and session constants."""

from __future__ import annotations

PAGE_SIZE = 5
SESSION_PAGE_KEY = "map_explorer_page"

SORT_OPTIONS: tuple[str, ...] = ("Priority Score", "Review count", "Destroyed %")
FILTER_OPTIONS: tuple[str, ...] = ("All", "Review Required", "Test")

HEADER_COLUMN_WEIGHTS: list[float] = [2.2, 1.3]
TOOLBAR_COLUMN_WEIGHTS: list[float] = [2.6, 1.1, 1.1]
BOTTOM_PANEL_COLUMN_WEIGHTS: list[float] = [1, 1]

# Table body + right-aligned Inspect actions column
TABLE_BODY_COLUMN_WEIGHTS: list[float] = [12, 1]

SORT_FIELD_KEYS: dict[str, str] = {
    "Review count": "review_flag_count",
    "Destroyed %": "destroyed_share",
}
