"""Interactive paired-image viewer for the dashboard scene explorer."""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass
from io import BytesIO

import streamlit.components.v1 as components
from PIL import Image

from src.dashboard.components.scene_viewer_layout import (
    SceneViewerLayout,
    compute_scene_viewer_layout,
)

CARD_BACKGROUND = "#161B22"
CARD_BORDER = "#2D3A4F"


@dataclass(frozen=True)
class ImagePane:
    """A single image pane shown in the paired scene viewer."""

    key: str
    label: str
    src: str
    alt: str
    width: int | None = None
    height: int | None = None


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
      --card-border: {CARD_BORDER};
      --pane-max-height: {layout.max_pane_height_px}px;
      --pane-aspect: {layout.pane_aspect_css};
      --text: #E8EDF4;
      --muted: #9AA8BC;
      --focus: #3B82F6;
      --control-bg: rgba(22, 27, 34, 0.82);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Inter", system-ui, sans-serif;
      color: var(--text);
      background: var(--card-bg);
    }}

    .viewer {{
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      background: var(--card-bg);
      overflow: hidden;
    }}

    .viewer-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.625rem 0.875rem;
      border-bottom: 1px solid var(--card-border);
    }}

    .viewer-title {{
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
    }}

    .viewer-confidence {{
      font-family: "IBM Plex Mono", ui-monospace, monospace;
      font-size: 0.75rem;
      color: var(--muted);
      white-space: nowrap;
    }}

    .viewer-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.75rem;
      padding: 0.75rem;
    }}

    .image-pane {{
      position: relative;
      width: 100%;
      aspect-ratio: var(--pane-aspect);
      max-height: var(--pane-max-height);
      margin: 0 auto;
      overflow: hidden;
      border-radius: 0.5rem;
      background: var(--card-bg);
    }}

    .image-pane img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
      object-position: center center;
      transform: scale(1);
      transform-origin: center center;
      transition: transform 130ms ease-out;
      user-select: none;
      -webkit-user-drag: none;
    }}

    .image-chip,
    .full-link,
    .zoom-controls {{
      position: absolute;
      z-index: 2;
      border: 1px solid var(--card-border);
      background: var(--control-bg);
      backdrop-filter: blur(4px);
    }}

    .image-chip {{
      top: 0.5rem;
      left: 0.5rem;
      max-width: calc(100% - 4.5rem);
      border-radius: 0.25rem;
      padding: 0.2rem 0.5rem;
      font-family: "IBM Plex Mono", ui-monospace, monospace;
      font-size: 0.7rem;
    }}

    .full-link {{
      top: 0.5rem;
      right: 0.5rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2rem;
      height: 2rem;
      border-radius: 0.4rem;
      color: var(--text);
      text-decoration: none;
    }}

    .zoom-controls {{
      right: 0.5rem;
      bottom: 0.5rem;
      display: inline-flex;
      align-items: center;
      gap: 0.1rem;
      border-radius: 0.45rem;
      padding: 0.1rem;
    }}

    .zoom-controls button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2rem;
      height: 2rem;
      padding: 0;
      border: 0;
      border-radius: 0.35rem;
      color: var(--muted);
      background: transparent;
      cursor: pointer;
    }}

    .zoom-controls button:hover,
    .full-link:hover {{
      background: rgba(255, 255, 255, 0.1);
      color: var(--text);
    }}

    .zoom-controls button:focus-visible,
    .full-link:focus-visible {{
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }}

    .material-symbols-outlined {{
      font-family: "Material Symbols Outlined";
      font-size: 1.2rem;
      line-height: 1;
      font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
    }}

    @media (max-width: 760px) {{
      .viewer-head {{
        align-items: flex-start;
        flex-direction: column;
        gap: 0.25rem;
      }}

      .viewer-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <section class="viewer" aria-label="Scene image comparison">
    <header class="viewer-head">
      <h3 class="viewer-title">{safe_title}</h3>
      <span class="viewer-confidence">{safe_confidence}</span>
    </header>
    <div class="viewer-grid">{pane_html}</div>
  </section>
  <script>
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    document.querySelectorAll(".image-pane").forEach((pane) => {{
      const image = pane.querySelector("img");
      let scale = 1;

      const setScale = (nextScale) => {{
        scale = clamp(nextScale, 1, 3);
        image.style.transform = `scale(${{scale}})`;
      }};

      pane.querySelectorAll("[data-zoom-action]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const action = button.dataset.zoomAction;
          if (action === "in") setScale(scale + 0.25);
          if (action === "out") setScale(scale - 0.25);
          if (action === "reset") setScale(1);
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def image_to_data_uri(image: Image.Image) -> str:
    """Encode a display image for the dashboard viewer."""
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _pane_html(pane: ImagePane) -> str:
    safe_key = html.escape(pane.key, quote=True)
    safe_src = html.escape(pane.src, quote=True)
    safe_label = html.escape(pane.label)
    safe_alt = html.escape(pane.alt, quote=True)
    safe_full_label = html.escape(f"View full {pane.label} image", quote=True)
    return f"""
      <figure class="image-pane" data-pane="{safe_key}">
        <img src="{safe_src}" alt="{safe_alt}" />
        <figcaption class="image-chip">{safe_label}</figcaption>
        <a
          class="full-link"
          href="{safe_src}"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="{safe_full_label}"
          title="View full image"
        >
          <span class="material-symbols-outlined" aria-hidden="true">open_in_full</span>
        </a>
        <div class="zoom-controls" aria-label="{safe_label} zoom controls">
          <button type="button" data-zoom-action="in" aria-label="Zoom in {safe_label}">
            <span class="material-symbols-outlined" aria-hidden="true">zoom_in</span>
          </button>
          <button type="button" data-zoom-action="out" aria-label="Zoom out {safe_label}">
            <span class="material-symbols-outlined" aria-hidden="true">zoom_out</span>
          </button>
          <button type="button" data-zoom-action="reset" aria-label="Reset zoom {safe_label}">
            <span class="material-symbols-outlined" aria-hidden="true">fit_screen</span>
          </button>
        </div>
      </figure>
"""
