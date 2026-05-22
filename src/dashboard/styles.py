from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit.components.v1 as components

_THEME_PATH = Path(__file__).parent / "theme.css"

_FONT_INTER = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=IBM+Plex+Mono:wght@400&display=swap"
_FONT_ICONS = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap"


def inject_theme() -> None:
    """Inject or refresh CSS in the parent document."""
    css = _THEME_PATH.read_text(encoding="utf-8")
    css_hash = hashlib.sha256(css.encode("utf-8")).hexdigest()
    css_json = json.dumps(css)
    css_hash_json = json.dumps(css_hash)
    inter_json = json.dumps(_FONT_INTER)
    icons_json = json.dumps(_FONT_ICONS)

    components.html(
        f"""
        <script>
        (function () {{
            const doc = window.parent.document;
            const cssHash = {css_hash_json};

            let style = doc.getElementById("ds-theme");
            if (!style) {{
                style = doc.createElement("style");
                style.id = "ds-theme";
                doc.head.appendChild(style);
            }}
            if (style.dataset.dsHash !== cssHash) {{
                style.textContent = {css_json};
                style.dataset.dsHash = cssHash;
            }}

            if (!doc.getElementById("ds-font-inter")) {{
                const inter = doc.createElement("link");
                inter.id = "ds-font-inter";
                inter.rel = "stylesheet";
                inter.href = {inter_json};
                doc.head.appendChild(inter);
            }}

            if (!doc.getElementById("ds-font-icons")) {{
                const icons = doc.createElement("link");
                icons.id = "ds-font-icons";
                icons.rel = "stylesheet";
                icons.href = {icons_json};
                doc.head.appendChild(icons);
            }}

            function dsStyleSidebarControls() {{
                const expand = doc.querySelector('button[data-testid="stExpandSidebarButton"]');
                if (expand) {{
                    expand.style.zIndex = "100023";
                }}
            }}

            if (!window.dsSidebarObserver) {{
                window.dsSidebarObserver = new MutationObserver(dsStyleSidebarControls);
                window.dsSidebarObserver.observe(doc.body, {{
                    childList: true,
                    subtree: true,
                }});
                dsStyleSidebarControls();
            }}
        }})();
        </script>
        """,
        height=0,
        scrolling=False,
    )


def icon(name: str, *, fill: bool = False, size: int = 24) -> str:
    """Material Symbols Outlined span."""
    fill_val = 1 if fill else 0
    return (
        f'<span class="material-symbols-outlined" aria-hidden="true" '
        f'style="font-size:{size}px;font-variation-settings:'
        f"'FILL' {fill_val},'wght' 400,'GRAD' 0,'opsz' 24\">"
        f"{name}</span>"
    )
