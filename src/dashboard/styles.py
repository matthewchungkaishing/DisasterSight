from __future__ import annotations

from pathlib import Path

import streamlit as st

_THEME_PATH = Path(__file__).parent / "theme.css"


def inject_theme() -> None:
    """Inject custom CSS for Stitch-aligned dark theme."""
    if st.session_state.get("_ds_theme_injected"):
        return
    css = _THEME_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.session_state["_ds_theme_injected"] = True
