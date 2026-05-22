from __future__ import annotations

import streamlit as st

from src.common.constants import DAMAGE_CLASSES, OVERLAY_COLORS
from src.dashboard.labels import display_label


def render(class_counts: dict[str, int], total: int | None = None) -> None:
    total = total or sum(class_counts.values()) or 1
    st.markdown('<h3 class="ds-panel-head">Severity Breakdown</h3>', unsafe_allow_html=True)
    order = list(DAMAGE_CLASSES)
    order.reverse()
    rows = ""
    for label in order:
        count = class_counts.get(label, 0)
        pct = 100 * count / total
        color = OVERLAY_COLORS.get(label, "#9AA8BC")
        name = display_label(label)
        rows += f"""
        <div class="ds-sev-row">
            <span class="ds-sev-name">{name}</span>
            <div class="ds-sev-track"><div class="ds-sev-fill" style="width:{pct:.0f}%;background:{color}"></div></div>
            <span class="ds-sev-pct">{pct:.0f}%</span>
        </div>
        """
    st.markdown(rows, unsafe_allow_html=True)
