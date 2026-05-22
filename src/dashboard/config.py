"""Dashboard configuration accessors.

Wraps :func:`src.common.paths.load_config` with dashboard-specific
convenience helpers.  Config is read once and cached for the process
lifetime via :func:`functools.lru_cache`.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from src.common.paths import PROJECT_ROOT, load_config, resolve_path

DASHBOARD_ROOT = Path(__file__).parent
FIXTURES_DIR = DASHBOARD_ROOT / "fixtures"


@functools.lru_cache(maxsize=1)
def get_dashboard_config() -> dict[str, Any]:
    """Return the full project config, cached for the process."""
    return load_config()


def get_paths() -> dict[str, Path]:
    """Resolved artifact and data paths from config.yaml."""
    cfg = get_dashboard_config()
    return {key: resolve_path(val, PROJECT_ROOT) for key, val in cfg.get("paths", {}).items()}


def get_priority_weights() -> dict[str, float]:
    """Priority-score component weights from config.yaml."""
    ps = get_dashboard_config().get("priority_score", {})
    return {
        "destroyed": float(ps.get("destroyed_weight", 0.50)),
        "major_damage": float(ps.get("major_damage_weight", 0.30)),
        "damage_density": float(ps.get("damage_density_weight", 0.20)),
    }


def get_inference_thresholds() -> dict[str, float]:
    """Confidence and review thresholds from config.yaml."""
    inf = get_dashboard_config().get("inference", {})
    return {
        "confidence": float(inf.get("confidence_threshold", 0.6)),
        "review": float(inf.get("review_threshold", 0.5)),
    }
