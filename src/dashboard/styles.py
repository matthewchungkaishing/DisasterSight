from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_THEME_PATH = Path(__file__).parent / "theme.css"

_FONT_INTER = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=IBM+Plex+Mono:wght@400&display=swap"
_FONT_ICONS = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap"


def inject_theme() -> None:
    """Inject CSS into the parent document (st.markdown strips <style> tags)."""
    if st.session_state.get("_ds_theme_injected"):
        return

    css = _THEME_PATH.read_text(encoding="utf-8")
    css_json = json.dumps(css)
    inter_json = json.dumps(_FONT_INTER)
    icons_json = json.dumps(_FONT_ICONS)

    components.html(
        f"""
        <script>
        (function () {{
            const doc = window.parent.document;
            if (doc.getElementById("ds-theme")) return;

            const style = doc.createElement("style");
            style.id = "ds-theme";
            style.textContent = {css_json};
            doc.head.appendChild(style);

            const inter = doc.createElement("link");
            inter.rel = "stylesheet";
            inter.href = {inter_json};
            doc.head.appendChild(inter);

            const icons = doc.createElement("link");
            icons.rel = "stylesheet";
            icons.href = {icons_json};
            doc.head.appendChild(icons);
        }})();
        </script>
        """,
        height=0,
        scrolling=False,
    )
    st.session_state["_ds_theme_injected"] = True


def icon(name: str, *, fill: bool = False, size: int = 24) -> str:
    """Material Symbols Outlined span."""
    fill_val = 1 if fill else 0
    return (
        f'<span class="material-symbols-outlined" aria-hidden="true" '
        f'style="font-size:{size}px;font-variation-settings:'
        f"'FILL' {fill_val},'wght' 400,'GRAD' 0,'opsz' 24\">"
        f"{name}</span>"
    )
