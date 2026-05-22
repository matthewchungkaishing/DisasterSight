from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.common.constants import DAMAGE_CLASSES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

REQUIRED_CONFIG_SECTIONS = ("project", "paths", "dataset", "labels")
REQUIRED_PATH_KEYS = (
    "data_root",
    "raw_data_dir",
    "xbd_root",
    "interim_data_dir",
    "processed_data_dir",
    "cache_dir",
    "artifacts_dir",
    "checkpoints_dir",
    "predictions_dir",
    "figures_dir",
    "manifests_dir",
)
GENERATED_PATH_KEYS = (
    "interim_data_dir",
    "processed_data_dir",
    "cache_dir",
    "artifacts_dir",
    "checkpoints_dir",
    "predictions_dir",
    "figures_dir",
    "manifests_dir",
)


def load_config(config_path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    """Load the project YAML configuration."""
    path = config_path or CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Config must be a YAML mapping: {path}")

    if validate:
        validate_config(config)

    return config


def validate_config(config: dict[str, Any]) -> None:
    """Fail fast when core project config drifts away from the MVP contract."""
    missing_sections = [section for section in REQUIRED_CONFIG_SECTIONS if section not in config]
    if missing_sections:
        raise ValueError(f"Config is missing required sections: {missing_sections}")

    path_config = config.get("paths", {})
    if not isinstance(path_config, dict):
        raise ValueError("Config section `paths` must be a mapping.")

    missing_paths = [key for key in REQUIRED_PATH_KEYS if key not in path_config]
    if missing_paths:
        raise ValueError(f"Config section `paths` is missing keys: {missing_paths}")

    for key, value in path_config.items():
        if not isinstance(value, str | Path):
            raise ValueError(f"Config path `{key}` must be a string path.")

    dataset_config = config.get("dataset", {})
    if not isinstance(dataset_config, dict):
        raise ValueError("Config section `dataset` must be a mapping.")

    for key in ("image_size", "crop_padding_pixels", "min_building_area_pixels"):
        if float(dataset_config.get(key, 0)) <= 0:
            raise ValueError(f"Config dataset `{key}` must be positive.")

    split_total = sum(
        float(dataset_config.get(key, 0.0)) for key in ("train_split", "val_split", "test_split")
    )
    if abs(split_total - 1.0) > 0.001:
        raise ValueError("Config train/val/test splits must sum to 1.0.")

    label_config = config.get("labels", {})
    if not isinstance(label_config, dict):
        raise ValueError("Config section `labels` must be a mapping.")

    configured_damage_classes = tuple(label_config.get("damage_classes", ()))
    if configured_damage_classes != DAMAGE_CLASSES:
        raise ValueError(
            "Config labels.damage_classes must match src.common.constants.DAMAGE_CLASSES."
        )


def resolve_path(value: str | Path, project_root: Path | None = None) -> Path:
    """Resolve a configured path relative to the repository root."""
    base = project_root or PROJECT_ROOT
    path = Path(value)
    return path if path.is_absolute() else base / path


def project_relative_path(path: Path, project_root: Path | None = None) -> str:
    """Return a portable repo-relative path when possible."""
    base = (project_root or PROJECT_ROOT).resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(base).as_posix()
    except ValueError:
        return str(resolved_path)


def get_path_map(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """Return the configured path section as resolved Path objects."""
    cfg = config or load_config()
    path_config = cfg.get("paths", {})
    return {key: resolve_path(value) for key, value in path_config.items()}


def ensure_project_dirs(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """Create configured local directories that store generated artifacts."""
    path_map = get_path_map(config)
    for key in GENERATED_PATH_KEYS:
        if key in path_map:
            path_map[key].mkdir(parents=True, exist_ok=True)
    return path_map
