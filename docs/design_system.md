# DisasterSight Design System

Stitch mockup references: [`design_refs/dashboard.png`](design_refs/dashboard.png), [`map_explorer.png`](design_refs/map_explorer.png), [`design_refs/analytics.png`](design_refs/analytics.png).

## Color tokens

| Token | Hex | Usage |
|-------|-----|--------|
| `bg_app` | `#765FEF` | Page background |
| `bg_sidebar` | `#121820` | Sidebar |
| `bg_card` | `#161B22` | KPI cards, panels |
| `bg_card_elevated` | `#1C252E` | Tables, widgets |
| `border` | `#2D3A4F` | Card borders |
| `text_primary` | `#E8EDF4` | Headings, values |
| `text_secondary` | `#9AA8BC` | Labels |
| `accent_primary` | `#3B82F6` | Active nav, Ready badge |
| `accent_info` | `#1E3A5F` | Info banners |

Damage severity colors are defined in `src/common/constants.py` (`OVERLAY_COLORS`) and used for legends, badges, charts, and overlays.

## Scene image viewer

- Layout math lives in `src/dashboard/components/scene_viewer_layout.py` (pure, testable).
- Rendering lives in `src/dashboard/components/scene_viewer/` (`builder.py` + `assets/viewer.css` + `assets/viewer.js`); orchestration in `scene_explorer.py`.
- Pre/post panes sit flush side-by-side (no grid gap). Images preserve aspect ratio without cropping; split mode aligns pre to the right edge and post to the left edge so the pair meets at the center seam.
- Zoom (buttons, wheel) and drag-pan while zoomed use a per-pane viewport controller in `viewer.js`.
- Full-width mode expands one pane across the card (open-in-full icon); close-fullscreen returns to the paired view.
- Pane height auto-adapts to slot width. An explicit cap can be set via `dashboard.scene_explorer_max_pane_height_px` in `config.yaml` if needed.
- Iframe height is computed from layout so content is not clipped on wide screens.

## Typography

- UI: Inter (Google Fonts), fallback system-ui
- IDs: IBM Plex Mono / ui-monospace

## Dashboard page hierarchy

- **Hero row** (~78% width): Scene Explorer; right sidebar with a **2×2 KPI quadrant** (`metrics/`), then Severity Breakdown below (padded separator).
- **Table row**: Top buildings by severity under Scene Explorer (left column, same width as viewer).
- Layout markers and column weights live in `dashboard_layout.py`; styles in `theme.css`.

## Spacing

8px grid: 8, 16, 24, 32. Card radius 12px, buttons 8px, chips fully rounded.

## Streamlit mapping

- Theme base: `.streamlit/config.toml`
- Overrides: `src/dashboard/theme.css` via `styles.inject_theme()`
