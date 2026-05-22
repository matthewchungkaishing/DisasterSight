"""Priority score computation and zone-summary builder for the dashboard."""

from __future__ import annotations

from src.common.priority_score import compute_priority_score, compute_shares
from src.dashboard.config import get_priority_weights


def build_zone_summary(
    scene_id: str,
    class_counts: dict[str, int],
    review_flag_count: int,
) -> dict[str, object]:
    """Build a zone-summary record conforming to the Zone Summary Contract."""
    total = sum(class_counts.values())
    shares = compute_shares(class_counts, total)
    weights = get_priority_weights()
    priority = compute_priority_score(
        shares["destroyed_share"],
        shares["major_damage_share"],
        shares["damage_density"],
        destroyed_weight=weights["destroyed"],
        major_damage_weight=weights["major_damage"],
        damage_density_weight=weights["damage_density"],
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
    """Return a CSS helper class for the given priority score."""
    if score >= 80:
        return "ds-priority-high"
    if score >= 50:
        return "ds-priority-mid"
    return "ds-priority-low"


def rationale_text(summary: dict[str, object], disaster_name: str) -> str:
    """Generate highest-priority rationale copy for Map Explorer."""
    sid = summary.get("scene_id", "")
    score = summary.get("priority_score", 0)
    dest = float(str(summary.get("destroyed_share", 0))) * 100
    major = float(str(summary.get("major_damage_share", 0))) * 100
    return (
        f"Score elevated to **{score}** for scene `{sid}` ({disaster_name}) due to "
        f"**{dest:.0f}%** destroyed and **{major:.0f}%** major-damage building share "
        f"in the assessed area. Human verification is required before resource prioritisation."
    )
