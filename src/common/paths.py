from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load the project YAML configuration."""
    path = config_path or CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_path(value: str | Path, project_root: Path | None = None) -> Path:
    """Resolve a configured path relative to the repository root."""
    base = project_root or PROJECT_ROOT
    path = Path(value)
    return path if path.is_absolute() else base / path


def get_path_map(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """Return the configured path section as resolved Path objects."""
    cfg = config or load_config()
    path_config = cfg.get("paths", {})
    return {key: resolve_path(value) for key, value in path_config.items()}


def ensure_project_dirs(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """Create configured local directories that store generated artifacts."""
    path_map = get_path_map(config)
    for path in path_map.values():
        path.mkdir(parents=True, exist_ok=True)
    return path_map
