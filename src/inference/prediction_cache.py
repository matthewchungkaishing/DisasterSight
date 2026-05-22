from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.common.constants import DAMAGE_CLASSES
from src.common.priority_score import compute_priority_score, compute_shares

PREDICTION_FIELDS = (
    "scene_id",
    "building_id",
    "disaster_name",
    "disaster_type",
    "split",
    "true_label",
    "predicted_label",
    "confidence",
    "needs_review",
    "class_probabilities",
    "polygon_xy",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "pre_crop_path",
    "post_crop_path",
)

SCENE_SUMMARY_FIELDS = (
    "scene_id",
    "disaster_name",
    "disaster_type",
    "split",
    "total_buildings",
    "class_counts",
    "destroyed_share",
    "major_damage_share",
    "damage_density",
    "priority_score",
    "review_flag_count",
    "mean_confidence",
)


@dataclass(frozen=True)
class PredictionRecord:
    scene_id: str
    building_id: str
    disaster_name: str
    disaster_type: str
    split: str
    true_label: str
    predicted_label: str
    confidence: float
    needs_review: bool
    class_probabilities: str
    polygon_xy: str
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int
    pre_crop_path: str
    post_crop_path: str


@dataclass(frozen=True)
class SceneSummary:
    scene_id: str
    disaster_name: str
    disaster_type: str
    split: str
    total_buildings: int
    class_counts: str
    destroyed_share: float
    major_damage_share: float
    damage_density: float
    priority_score: float
    review_flag_count: int
    mean_confidence: float


def read_crop_manifest(path: Path) -> list[dict[str, str]]:
    """Load crop manifest rows for cached inference."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def filter_crop_rows(
    rows: list[dict[str, str]],
    *,
    split: str | None = None,
    scene_ids: set[str] | None = None,
    scene_limit: int | None = None,
) -> list[dict[str, str]]:
    """Filter crop rows while preserving manifest order."""
    selected = []
    seen_scenes: set[str] = set()

    for row in rows:
        if split is not None and row.get("split") != split:
            continue
        if scene_ids is not None and row.get("scene_id") not in scene_ids:
            continue

        scene_id = row.get("scene_id", "")
        if (
            scene_limit is not None
            and scene_id not in seen_scenes
            and len(seen_scenes) >= scene_limit
        ):
            continue

        selected.append(row)
        if scene_id:
            seen_scenes.add(scene_id)

    return selected


def build_prediction_records(
    crop_rows: list[dict[str, str]],
    probabilities: list[list[float]],
    *,
    confidence_threshold: float,
) -> list[PredictionRecord]:
    """Attach model probabilities to crop metadata and flag low-confidence predictions."""
    if len(crop_rows) != len(probabilities):
        raise ValueError("crop_rows and probabilities must have the same length.")

    records: list[PredictionRecord] = []
    for row, probs in zip(crop_rows, probabilities, strict=True):
        if len(probs) != len(DAMAGE_CLASSES):
            raise ValueError("Each probability row must match DAMAGE_CLASSES length.")

        predicted_idx = max(range(len(probs)), key=probs.__getitem__)
        confidence = float(probs[predicted_idx])
        prob_map = {
            label: round(float(probs[index]), 6) for index, label in enumerate(DAMAGE_CLASSES)
        }

        records.append(
            PredictionRecord(
                scene_id=row.get("scene_id", ""),
                building_id=row.get("building_id", ""),
                disaster_name=row.get("disaster_name", ""),
                disaster_type=row.get("disaster_type", ""),
                split=row.get("split", ""),
                true_label=row.get("damage_label", ""),
                predicted_label=DAMAGE_CLASSES[predicted_idx],
                confidence=round(confidence, 6),
                needs_review=confidence < confidence_threshold,
                class_probabilities=json.dumps(prob_map, separators=(",", ":")),
                polygon_xy=row.get("polygon_xy", "[]"),
                bbox_x1=_to_int(row.get("bbox_x1", "0")),
                bbox_y1=_to_int(row.get("bbox_y1", "0")),
                bbox_x2=_to_int(row.get("bbox_x2", "0")),
                bbox_y2=_to_int(row.get("bbox_y2", "0")),
                pre_crop_path=row.get("pre_crop_path", ""),
                post_crop_path=row.get("post_crop_path", ""),
            )
        )

    return records


def summarise_scene_predictions(
    records: list[PredictionRecord],
    *,
    destroyed_weight: float,
    major_damage_weight: float,
    damage_density_weight: float,
) -> list[SceneSummary]:
    """Aggregate building predictions into dashboard-ready scene summaries."""
    grouped: dict[str, list[PredictionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.scene_id].append(record)

    summaries: list[SceneSummary] = []
    for scene_id in sorted(grouped):
        scene_records = grouped[scene_id]
        first = scene_records[0]
        total = len(scene_records)
        counts = Counter(record.predicted_label for record in scene_records)
        class_counts = {label: counts.get(label, 0) for label in DAMAGE_CLASSES}
        shares = compute_shares(class_counts, total)
        priority_score = compute_priority_score(
            shares["destroyed_share"],
            shares["major_damage_share"],
            shares["damage_density"],
            destroyed_weight=destroyed_weight,
            major_damage_weight=major_damage_weight,
            damage_density_weight=damage_density_weight,
        )
        destroyed_share = shares["destroyed_share"]
        major_damage_share = shares["major_damage_share"]
        damage_density = shares["damage_density"]
        review_flag_count = sum(record.needs_review for record in scene_records)
        mean_confidence = sum(record.confidence for record in scene_records) / total

        summaries.append(
            SceneSummary(
                scene_id=scene_id,
                disaster_name=first.disaster_name,
                disaster_type=first.disaster_type,
                split=first.split,
                total_buildings=total,
                class_counts=json.dumps(class_counts, separators=(",", ":")),
                destroyed_share=round(destroyed_share, 6),
                major_damage_share=round(major_damage_share, 6),
                damage_density=round(damage_density, 6),
                priority_score=round(priority_score, 2),
                review_flag_count=review_flag_count,
                mean_confidence=round(mean_confidence, 6),
            )
        )

    return summaries


def write_prediction_csv(path: Path, records: list[PredictionRecord]) -> None:
    _write_dataclass_csv(path, PREDICTION_FIELDS, records)


def write_scene_summary_csv(path: Path, summaries: list[SceneSummary]) -> None:
    _write_dataclass_csv(path, SCENE_SUMMARY_FIELDS, summaries)


def _write_dataclass_csv(path: Path, fieldnames: tuple[str, ...], rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
