"""Damage badge HTML snippet."""

from __future__ import annotations

from src.dashboard.labels import badge_class, display_label
from src.dashboard.styles import icon


def render_html(label: str) -> str:
    """Return an inline HTML badge for the given damage label."""
    css_class = badge_class(label)
    text = display_label(label)
    warn = icon("warning", size=14) if css_class in ("major_damage", "destroyed") else ""
    return f'<span class="ds-badge ds-badge-{css_class}">{warn}<span>{text}</span></span>'
