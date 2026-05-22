from __future__ import annotations

import streamlit as st

from src.common.constants import DAMAGE_CLASSES, OVERLAY_COLORS
from src.dashboard.labels import display_label


def render(class_counts: dict[str, int], total: int | None = None) -> None:
    """Horizontal severity breakdown bars."""
    total = total or sum(class_counts.values()) or 1
    st.markdown('<div class="ds-panel-title">Severity Breakdown</div>', unsafe_allow_html=True)
    order = list(DAMAGE_CLASSES)
    order.reverse()
    for label in order:
        count = class_counts.get(label, 0)
        pct = 100 * count / total
        color = OVERLAY_COLORS.get(label, "#9AA8BC")
        name = display_label(label)
        st.markdown(
            f"""
            <div class="ds-severity-row">
                <div class="ds-severity-label"><span>{name}</span><span>{pct:.0f}%</span></div>
                <div class="ds-severity-bar-bg">
                    <div class="ds-severity-bar-fill" style="width:{pct:.1f}%;background:{color}"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
