"""HTML builder for the Scene Explorer interactive viewer."""

from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

from src.dashboard.components.scene_viewer.models import ImagePane
from src.dashboard.components.scene_viewer_layout import (
    SceneViewerLayout,
    compute_scene_viewer_layout,
)

_ASSETS_DIR = Path(__file__).parent / "assets"
CARD_BACKGROUND = "#2A3348"
_CARD_BORDER = "#3D4A66"


@lru_cache(maxsize=1)
def _load_asset(name: str) -> str:
    return (_ASSETS_DIR / name).read_text(encoding="utf-8")


def render_scene_viewer(
    title: str,
    confidence_label: str,
    panes: tuple[ImagePane, ImagePane],
    layout: SceneViewerLayout | None = None,
) -> None:
    """Render the interactive viewer as an isolated Streamlit component."""
    resolved_layout = layout or _layout_from_panes(panes)
    components.html(
        build_scene_viewer_html(title, confidence_label, panes, resolved_layout),
        height=resolved_layout.component_height_px,
        scrolling=False,
    )


def _layout_from_panes(panes: tuple[ImagePane, ImagePane]) -> SceneViewerLayout:
    reference = next((pane for pane in panes if pane.width and pane.height), panes[0])
    return compute_scene_viewer_layout(reference.width or 1, reference.height or 1)


def build_scene_viewer_html(
    title: str,
    confidence_label: str,
    panes: tuple[ImagePane, ImagePane],
    layout: SceneViewerLayout,
) -> str:
    """Build the self-contained HTML for the image viewer."""
    pane_html = "".join(_pane_html(pane) for pane in panes)
    safe_title = html.escape(title)
    safe_confidence = html.escape(confidence_label)
    viewer_css = _load_asset("viewer.css")
    viewer_js = _load_asset("viewer.js")
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=IBM+Plex+Mono:wght@400&display=swap"
    rel="stylesheet"
  />
  <link
    href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap"
    rel="stylesheet"
  />
  <style>
    :root {{
      --card-bg: {CARD_BACKGROUND};
      --card-border: {_CARD_BORDER};
      --pane-max-height: {layout.max_pane_height_px}px;
      --text: #E8EDF4;
      --muted: #9AA8BC;
      --focus: #3B82F6;
      --control-bg: rgba(42, 51, 72, 0.92);
    }}
    {viewer_css}
  </style>
</head>
<body>
  <section class="scene-viewer" data-view-mode="split" aria-label="Scene image comparison">
    <header class="scene-viewer__head">
      <h3 class="scene-viewer__title">{safe_title}</h3>
      <span class="scene-viewer__confidence">{safe_confidence}</span>
    </header>
    <div class="scene-viewer__grid">{pane_html}</div>
  </section>
  <script>{viewer_js}</script>
</body>
</html>
"""


def _pane_html(pane: ImagePane) -> str:
    safe_key = html.escape(pane.key, quote=True)
    safe_src = html.escape(pane.src, quote=True)
    safe_label = html.escape(pane.label)
    safe_alt = html.escape(pane.alt, quote=True)
    safe_solo_label = html.escape(f"Expand {pane.label} to full width", quote=True)
    safe_split_label = html.escape("Return to side-by-side view", quote=True)
    aspect_width = pane.width or 1
    aspect_height = pane.height or 1
    return f"""
      <div class="pane-slot">
        <figure
          class="pane"
          data-pane="{safe_key}"
          data-aspect-width="{aspect_width}"
          data-aspect-height="{aspect_height}"
        >
          <div class="pane-viewport" aria-label="{safe_label} viewport">
            <div class="pane-layer">
              <img src="{safe_src}" alt="{safe_alt}" />
            </div>
          </div>
          <figcaption class="pane-chip">{safe_label}</figcaption>
          <button
            class="pane-mode-btn"
            type="button"
            data-mode-action="solo"
            data-pane-key="{safe_key}"
            aria-label="{safe_solo_label}"
            title="Full-width view"
          >
            <span class="material-symbols-outlined" aria-hidden="true">open_in_full</span>
          </button>
          <button
            class="pane-mode-btn"
            type="button"
            data-mode-action="split"
            data-pane-key="{safe_key}"
            aria-label="{safe_split_label}"
            title="Side-by-side view"
          >
            <span class="material-symbols-outlined" aria-hidden="true">close_fullscreen</span>
          </button>
        </figure>
      </div>
"""
