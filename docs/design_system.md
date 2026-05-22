# DisasterSight Design System

Stitch mockup references: [`design_refs/dashboard.png`](design_refs/dashboard.png), [`map_explorer.png`](design_refs/map_explorer.png), [`design_refs/analytics.png`](design_refs/analytics.png).

## Color tokens

| Token | Hex | Usage |
|-------|-----|--------|
| `bg_app` | `#0B0E14` | Page background |
| `bg_sidebar` | `#121820` | Sidebar |
| `bg_card` | `#161B22` | KPI cards, panels |
| `bg_card_elevated` | `#1C252E` | Tables, widgets |
| `border` | `#2D3A4F` | Card borders |
| `text_primary` | `#E8EDF4` | Headings, values |
| `text_secondary` | `#9AA8BC` | Labels |
| `accent_primary` | `#3B82F6` | Active nav, Ready badge |
| `accent_info` | `#1E3A5F` | Info banners |

Damage severity colors are defined in `src/common/constants.py` (`OVERLAY_COLORS`) and used for legends, badges, charts, and overlays.

## Typography

- UI: Inter (Google Fonts), fallback system-ui
- IDs: IBM Plex Mono / ui-monospace

## Spacing

8px grid: 8, 16, 24, 32. Card radius 12px, buttons 8px, chips fully rounded.

## Streamlit mapping

- Theme base: `.streamlit/config.toml`
- Overrides: `src/dashboard/theme.css` via `styles.inject_theme()`
