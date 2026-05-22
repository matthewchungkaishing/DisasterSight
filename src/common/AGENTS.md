# AGENTS.md — src/common/

## Module purpose

Shared constants, configuration loading, and path utilities used across all DisasterSight packages.

## Key files

- `constants.py` — canonical damage classes, class-to-index mappings, overlay colours, metric names, priority score formula.
- `paths.py` — `load_config()`, `validate_config()`, `resolve_path()`, `project_relative_path()`, path maps.

## Key conventions

- `DAMAGE_CLASSES` is the single source of truth for label ordering. All other modules import from here.
- `config.yaml` is loaded and validated via `load_config()`. Config must include `project`, `paths`, `dataset`, and `labels` sections.
- All generated directories are created via `ensure_project_dirs()`.
- Paths are resolved relative to `PROJECT_ROOT` (two levels up from this package).

## What not to do

- Do not define damage classes or label mappings anywhere else — always import from `constants.py`.
- Do not add heavyweight dependencies (torch, pandas, etc.) to this package — keep it lightweight.
- Do not change `DAMAGE_CLASSES` ordering without updating `config.yaml`, `interface_contracts.md`, and all downstream code.
