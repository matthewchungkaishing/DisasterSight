"""Shared priority-score computation for inference and dashboard layers."""

from __future__ import annotations

from src.common.constants import DAMAGE_CLASSES


def compute_shares(class_counts: dict[str, int], total: int) -> dict[str, float]:
    """Compute destroyed share, major-damage share, and damage density."""
    if total <= 0:
        return {"destroyed_share": 0.0, "major_damage_share": 0.0, "damage_density": 0.0}
    destroyed = class_counts.get("destroyed", 0)
    major = class_counts.get("major_damage", 0)
    damaged = sum(class_counts.get(label, 0) for label in DAMAGE_CLASSES if label != "no_damage")
    return {
        "destroyed_share": destroyed / total,
        "major_damage_share": major / total,
        "damage_density": damaged / total,
    }


def compute_priority_score(
    destroyed_share: float,
    major_damage_share: float,
    damage_density: float,
    *,
    destroyed_weight: float = 0.50,
    major_damage_weight: float = 0.30,
    damage_density_weight: float = 0.20,
) -> float:
    """Demo priority score per the interface contract formula."""
    score = (
        destroyed_weight * destroyed_share
        + major_damage_weight * major_damage_share
        + damage_density_weight * damage_density
    )
    return round(100 * score, 2)


def priority_weights_from_config(priority_cfg: dict[str, float | int | str]) -> dict[str, float]:
    """Extract priority weights from a config ``priority_score`` section."""
    return {
        "destroyed": float(priority_cfg.get("destroyed_weight", 0.50)),
        "major_damage": float(priority_cfg.get("major_damage_weight", 0.30)),
        "damage_density": float(priority_cfg.get("damage_density_weight", 0.20)),
    }
