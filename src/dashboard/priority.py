from __future__ import annotations

from src.common.constants import DAMAGE_CLASSES
from src.dashboard.config import get_priority_weights


def compute_shares(class_counts: dict[str, int], total: int) -> dict[str, float]:
    """Compute destroyed share, major share, and damage density."""
    if total <= 0:
        return {"destroyed_share": 0.0, "major_damage_share": 0.0, "damage_density": 0.0}
    destroyed = class_counts.get("destroyed", 0)
    major = class_counts.get("major_damage", 0)
    damaged = sum(class_counts.get(c, 0) for c in DAMAGE_CLASSES if c != "no_damage")
    return {
        "destroyed_share": destroyed / total,
        "major_damage_share": major / total,
        "damage_density": damaged / total,
    }


def compute_priority_score(
    destroyed_share: float,
    major_damage_share: float,
    damage_density: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Demo priority score per interface contract."""
    w = weights or get_priority_weights()
    score = (
        w["destroyed"] * destroyed_share
        + w["major_damage"] * major_damage_share
        + w["damage_density"] * damage_density
    )
    return round(100 * score, 1)


def build_zone_summary(scene_id: str, class_counts: dict[str, int], review_flag_count: int) -> dict:
    """Build zone summary record for dashboard."""
    total = sum(class_counts.values())
    shares = compute_shares(class_counts, total)
    priority = compute_priority_score(
        shares["destroyed_share"],
        shares["major_damage_share"],
        shares["damage_density"],
    )
    return {
        "scene_id": scene_id,
        "total_buildings": total,
        "class_counts": class_counts,
        "destroyed_share": round(shares["destroyed_share"], 4),
        "major_damage_share": round(shares["major_damage_share"], 4),
        "damage_density": round(shares["damage_density"], 4),
        "priority_score": priority,
        "review_flag_count": review_flag_count,
    }


def priority_css_class(score: float) -> str:
    if score >= 80:
        return "ds-priority-high"
    if score >= 50:
        return "ds-priority-mid"
    return "ds-priority-low"


def rationale_text(summary: dict, disaster_name: str) -> str:
    """Generate highest-priority rationale copy for Map Explorer."""
    sid = summary.get("scene_id", "")
    score = summary.get("priority_score", 0)
    dest = summary.get("destroyed_share", 0) * 100
    major = summary.get("major_damage_share", 0) * 100
    return (
        f"Score elevated to **{score}** for scene `{sid}` ({disaster_name}) due to "
        f"**{dest:.0f}%** destroyed and **{major:.0f}%** major-damage building share "
        f"in the assessed area. Human verification is required before resource prioritisation."
    )
