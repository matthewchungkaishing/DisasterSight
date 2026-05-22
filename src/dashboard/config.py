from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.paths import PROJECT_ROOT, load_config, resolve_path

DASHBOARD_ROOT = Path(__file__).parent
FIXTURES_DIR = DASHBOARD_ROOT / "fixtures"


def get_dashboard_config() -> dict[str, Any]:
    """Return full project config."""
    return load_config()


def get_paths() -> dict[str, Path]:
    """Resolved artifact and data paths."""
    cfg = load_config()
    paths = cfg.get("paths", {})
    return {key: resolve_path(value, PROJECT_ROOT) for key, value in paths.items()}


def get_priority_weights() -> dict[str, float]:
    """Priority score weights from config.yaml."""
    cfg = load_config()
    ps = cfg.get("priority_score", {})
    return {
        "destroyed": float(ps.get("destroyed_weight", 0.50)),
        "major_damage": float(ps.get("major_damage_weight", 0.30)),
        "damage_density": float(ps.get("damage_density_weight", 0.20)),
    }


def get_inference_thresholds() -> dict[str, float]:
    cfg = load_config()
    inf = cfg.get("inference", {})
    return {
        "confidence": float(inf.get("confidence_threshold", 0.6)),
        "review": float(inf.get("review_threshold", 0.5)),
    }
