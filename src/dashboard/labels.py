"""Label normalization and display helpers for the dashboard.

Maps xBD hyphenated labels and other variants to the canonical
underscore form defined in :mod:`src.common.constants`.
"""

from __future__ import annotations

from src.common.constants import DAMAGE_CLASSES, REVIEW_REQUIRED_LABEL

_XBD_TO_CONTRACT: dict[str, str] = {
    "no-damage": "no_damage",
    "minor-damage": "minor_damage",
    "major-damage": "major_damage",
    "destroyed": "destroyed",
    "un-classified": "unclassified",
    "unclassified": "unclassified",
}

_CONTRACT_TO_DISPLAY: dict[str, str] = {
    "no_damage": "NO DAMAGE",
    "minor_damage": "MINOR",
    "major_damage": "MAJOR",
    "destroyed": "DESTROYED",
    REVIEW_REQUIRED_LABEL: "REVIEW REQUIRED",
}


def normalize_label(label: str | None) -> str:
    """Map xBD hyphenated labels or free-text variants to contract form."""
    if not label:
        return "unknown"
    cleaned = label.strip().lower().replace(" ", "-")
    if cleaned in _XBD_TO_CONTRACT:
        return _XBD_TO_CONTRACT[cleaned]
    normalized = cleaned.replace("-", "_")
    if normalized in DAMAGE_CLASSES or normalized == REVIEW_REQUIRED_LABEL:
        return normalized
    return normalized


def display_label(label: str) -> str:
    """Human-readable uppercase label for UI badges."""
    key = normalize_label(label)
    return _CONTRACT_TO_DISPLAY.get(key, key.replace("_", " ").upper())


def badge_class(label: str) -> str:
    """CSS class suffix for a damage badge."""
    key = normalize_label(label)
    if key in DAMAGE_CLASSES:
        return key
    return REVIEW_REQUIRED_LABEL
