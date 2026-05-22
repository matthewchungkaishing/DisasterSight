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
- Rendering lives in `src/dashboard/components/image_viewer.py`; orchestration in `scene_explorer.py`.
- Single card surface (`#161B22`) — no nested black/grey pane backgrounds; iframe body is transparent.
- Panes use native image `aspect-ratio` with `object-fit: contain` so imagery scales within each pane without cropping (letterboxing may appear when aspect ratios differ).
- Pane height cap: `dashboard.scene_explorer_max_pane_height_px` in `config.yaml` (default 420px).
- Iframe height is computed from layout so content is not clipped on wide screens.

## Typography

- UI: Inter (Google Fonts), fallback system-ui
- IDs: IBM Plex Mono / ui-monospace

## Spacing

8px grid: 8, 16, 24, 32. Card radius 12px, buttons 8px, chips fully rounded.

## Streamlit mapping

- Theme base: `.streamlit/config.toml`
- Overrides: `src/dashboard/theme.css` via `styles.inject_theme()`
