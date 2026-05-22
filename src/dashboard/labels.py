from __future__ import annotations

from src.common.constants import DAMAGE_CLASSES, REVIEW_REQUIRED_LABEL

_XBD_TO_CONTRACT = {
    "no-damage": "no_damage",
    "minor-damage": "minor_damage",
    "major-damage": "major_damage",
    "destroyed": "destroyed",
    "un-classified": "unclassified",
    "unclassified": "unclassified",
}

_CONTRACT_TO_DISPLAY = {
    "no_damage": "NO DAMAGE",
    "minor_damage": "MINOR",
    "major_damage": "MAJOR",
    "destroyed": "DESTROYED",
    "review_required": "REVIEW REQUIRED",
}


def normalize_label(label: str | None) -> str:
    """Map xBD hyphen labels or variants to contract underscore form."""
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
    """CSS class suffix for damage badge."""
    key = normalize_label(label)
    if key == "review_required" or key == REVIEW_REQUIRED_LABEL:
        return "review_required"
    if key in DAMAGE_CLASSES:
        return key
    return "review_required"
