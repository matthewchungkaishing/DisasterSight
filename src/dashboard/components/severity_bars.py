"""Severity breakdown bar chart component."""

from __future__ import annotations

import streamlit as st

from src.common.constants import DAMAGE_CLASSES, OVERLAY_COLORS
from src.dashboard.labels import display_label


def render(
    class_counts: dict[str, int],
    total: int | None = None,
    *,
    compact: bool = False,
    sidebar: bool = False,
) -> None:
    """Render horizontal severity bars for each damage class."""
    total = total or sum(class_counts.values()) or 1
    panel_bits = ["ds-panel"]
    if compact:
        panel_bits.append("ds-panel--compact")
    if sidebar:
        panel_bits.append("ds-panel--sidebar")
    panel_class = " ".join(panel_bits)

    rows = ""
    for label in reversed(DAMAGE_CLASSES):
        count = class_counts.get(label, 0)
        pct = 100 * count / total
        color = OVERLAY_COLORS.get(label, "#9AA8BC")
        name = display_label(label)
        rows += (
            f'<div class="ds-sev-row">'
            f'<span class="ds-sev-name">{name}</span>'
            f'<div class="ds-sev-track">'
            f'<div class="ds-sev-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'
            f'<span class="ds-sev-pct">{pct:.0f}%</span></div>'
        )
    panel_html = (
        f'<div class="{panel_class}"><h3 class="ds-panel-head">Severity Breakdown</h3>{rows}</div>'
    )
    if sidebar:
        panel_html = f'<div class="ds-hero-sidebar-severity">{panel_html}</div>'
    st.markdown(panel_html, unsafe_allow_html=True)
