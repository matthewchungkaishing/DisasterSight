from __future__ import annotations

from src.dashboard.labels import badge_class, display_label
from src.dashboard.styles import icon


def render_html(label: str) -> str:
    css_class = badge_class(label)
    text = display_label(label)
    warn = ""
    if css_class in ("major_damage", "destroyed"):
        warn = icon("warning", size=14)
    return f'<span class="ds-badge ds-badge-{css_class}">{warn}<span>{text}</span></span>'
