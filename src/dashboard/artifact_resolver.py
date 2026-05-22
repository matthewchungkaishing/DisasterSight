"""Pure artifact resolution and I/O helpers for dashboard data.

This module contains *no* Streamlit imports.  All functions are pure,
deterministic, and safe to call in unit tests or CLI scripts.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.metrics_format import format_dashboard_metrics
from src.common.paths import PROJECT_ROOT, get_path_map

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _resolved_paths() -> dict[str, Path]:
    """Config-driven artifact / data paths, resolved against the repo root."""
    return get_path_map()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _load_csv_as_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# CSV row parsers — convert raw CSV strings to typed dashboard dicts
# ---------------------------------------------------------------------------


def _parse_prediction_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Convert a building_predictions CSV row to the dashboard's expected format."""
    result: dict[str, Any] = dict(row)

    if "class_probabilities" in result and isinstance(result["class_probabilities"], str):
        try:
            result["class_probabilities"] = json.loads(result["class_probabilities"])
        except (json.JSONDecodeError, TypeError):
            result["class_probabilities"] = {}

    if "needs_review" in result:
        result["needs_review"] = str(result["needs_review"]).lower() in ("true", "1", "yes")

    for field in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"):
        if field in result:
            try:
                result[field] = int(result[field])
            except (ValueError, TypeError):
                result[field] = 0

    if "confidence" in result:
        try:
            result["confidence"] = float(result["confidence"])
        except (ValueError, TypeError):
            result["confidence"] = 0.0

    return result


def _parse_scene_summary_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Convert a scene_summaries CSV row to the dashboard's expected format."""
    result: dict[str, Any] = dict(row)

    if "class_counts" in result and isinstance(result["class_counts"], str):
        try:
            result["class_counts"] = json.loads(result["class_counts"])
        except (json.JSONDecodeError, TypeError):
            result["class_counts"] = {}

    for field in ("total_buildings", "review_flag_count"):
        if field in result:
            try:
                result[field] = int(result[field])
            except (ValueError, TypeError):
                result[field] = 0

    for field in (
        "destroyed_share",
        "major_damage_share",
        "damage_density",
        "priority_score",
        "mean_confidence",
    ):
        if field in result:
            try:
                result[field] = float(result[field])
            except (ValueError, TypeError):
                result[field] = 0.0

    return result


def _normalize_eval_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert evaluate.py eval_results format to the dashboard metrics format."""
    return format_dashboard_metrics(raw)


# ---------------------------------------------------------------------------
# Public resolvers
# ---------------------------------------------------------------------------


def resolve_scenes(paths: dict[str, Path] | None = None) -> tuple[list[dict[str, Any]], bool]:
    """Locate and load scene records.

    Returns ``(records, is_fixture)`` so the caller can decide whether to
    show a fixture warning.
    """
    p = paths or _resolved_paths()
    candidates = [
        p.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "scenes.json",
        p.get("manifests_dir", PROJECT_ROOT / "artifacts/manifests") / "scenes.json",
        p.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "scenes.csv",
        p.get("manifests_dir", PROJECT_ROOT / "artifacts/manifests") / "scene_manifest.csv",
        p.get("manifests_dir", PROJECT_ROOT / "artifacts/manifests") / "scene_manifest_small.csv",
    ]
    found = _first_existing(candidates)
    if found is not None:
        if found.suffix == ".csv":
            return _load_csv_as_dicts(found), False
        data = _load_json(found)
        if isinstance(data, list):
            return data, False
    return _load_json(FIXTURES_DIR / "demo_scenes.json"), True


def resolve_zone_summaries(
    paths: dict[str, Path] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Locate and load zone-level priority summaries.

    Resolution order:
    1. ``artifacts/zone_summaries.json``
    2. ``data/processed/zone_summaries.json``
    3. ``artifacts/predictions/scene_summaries_*.csv`` (inference pipeline output)
    4. Demo fixture fallback
    """
    p = paths or _resolved_paths()
    candidates = [
        p.get("artifacts_dir", PROJECT_ROOT / "artifacts") / "zone_summaries.json",
        p.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "zone_summaries.json",
    ]
    found = _first_existing(candidates)
    if found is not None:
        data = _load_json(found)
        if isinstance(data, list):
            return _sort_by_priority(data), False

    # Load from inference CSV outputs (most recent split takes priority)
    pred_dir = p.get("predictions_dir", PROJECT_ROOT / "artifacts/predictions")
    for split in ("test", "val", "train"):
        csv_path = pred_dir / f"scene_summaries_{split}.csv"
        if csv_path.exists():
            rows = _load_csv_as_dicts(csv_path)
            parsed = [_parse_scene_summary_csv_row(r) for r in rows]
            if parsed:
                return _sort_by_priority(parsed), False

    fixture = _load_json(FIXTURES_DIR / "demo_zone_summaries.json")
    return _sort_by_priority(fixture), True


def resolve_predictions(
    scene_id: str,
    paths: dict[str, Path] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Load building-level predictions for *scene_id*.

    Returns ``(records, is_fixture)``.

    Resolution order:
    1. ``{predictions_dir}/{scene_id}.json``
    2. ``{predictions_dir}/{scene_id}.jsonl``
    3. ``{predictions_dir}/predictions.parquet``
    4. ``{predictions_dir}/building_predictions_*.csv`` (inference pipeline output)
    5. Demo fixture fallback
    """
    p = paths or _resolved_paths()
    pred_dir = p.get("predictions_dir", PROJECT_ROOT / "artifacts/predictions")

    # Per-scene JSON/JSONL files and combined parquet
    direct_candidates = [
        pred_dir / f"{scene_id}.json",
        pred_dir / f"{scene_id}.jsonl",
        pred_dir / "predictions.parquet",
    ]
    for candidate in direct_candidates:
        if not candidate.exists():
            continue
        if candidate.suffix == ".parquet":
            df = pd.read_parquet(candidate)
            if "scene_id" in df.columns:
                df = df[df["scene_id"] == scene_id]
            return list(df.to_dict(orient="records")), False
        if candidate.suffix == ".jsonl":
            rows = [r for r in _load_jsonl(candidate) if r.get("scene_id") == scene_id]
            if rows:
                return rows, False
        else:
            data = _load_json(candidate)
            rows = data if isinstance(data, list) else data.get("predictions", [])
            filtered = [r for r in rows if r.get("scene_id") == scene_id]
            if filtered:
                return filtered, False

    # Inference pipeline CSV outputs
    for split in ("test", "val", "train"):
        csv_path = pred_dir / f"building_predictions_{split}.csv"
        if csv_path.exists():
            rows_raw = _load_csv_as_dicts(csv_path)
            scene_rows = [
                _parse_prediction_csv_row(r) for r in rows_raw if r.get("scene_id") == scene_id
            ]
            if scene_rows:
                return scene_rows, False

    # Fixture fallback — scene-scoped only; no cross-scene bleed
    fixture = _load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl")
    return [r for r in fixture if r.get("scene_id") == scene_id], True


def resolve_prediction_scene_ids(paths: dict[str, Path] | None = None) -> set[str]:
    """Return scene IDs present in cached prediction artifacts."""
    p = paths or _resolved_paths()
    pred_dir = p.get("predictions_dir", PROJECT_ROOT / "artifacts/predictions")
    scene_ids: set[str] = set()

    for split in ("test", "val", "train"):
        csv_path = pred_dir / f"building_predictions_{split}.csv"
        if not csv_path.exists():
            continue
        for row in _load_csv_as_dicts(csv_path):
            scene_id = row.get("scene_id")
            if scene_id:
                scene_ids.add(str(scene_id))

    if scene_ids:
        return scene_ids

    for row in _load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl"):
        scene_id = row.get("scene_id")
        if scene_id:
            scene_ids.add(str(scene_id))
    return scene_ids


def resolve_metrics(paths: dict[str, Path] | None = None) -> tuple[dict[str, Any], bool]:
    """Load evaluation metrics JSON.

    Returns ``(metrics, is_fixture)`` so callers can warn when using demo data.

    Resolution order:
    1. ``artifacts/metrics.json``
    2. ``artifacts/figures/metrics.json``  (legacy copy from evaluate.py)
    3. ``artifacts/figures/eval_results_{split}.json``  (normalized on load)
    4. Demo fixture fallback
    """
    p = paths or _resolved_paths()
    figures = p.get("figures_dir", PROJECT_ROOT / "artifacts/figures")
    candidates = [
        p.get("artifacts_dir", PROJECT_ROOT / "artifacts") / "metrics.json",
        figures / "metrics.json",
    ]
    found = _first_existing(candidates)
    if found is not None:
        return _load_json(found), False

    for split in ("test", "val"):
        eval_path = figures / f"eval_results_{split}.json"
        if eval_path.exists():
            return _normalize_eval_metrics(_load_json(eval_path)), False

    fallback: dict[str, Any] = _load_json(FIXTURES_DIR / "demo_metrics.json")
    return fallback, True


def resolve_confusion_matrix_image(paths: dict[str, Path] | None = None) -> Path | None:
    """Return the path to a confusion-matrix image if it exists."""
    p = paths or _resolved_paths()
    figures = p.get("figures_dir", PROJECT_ROOT / "artifacts/figures")
    return _first_existing(
        [
            figures / "confusion_matrix.png",
            figures / "confusion_matrix.jpg",
            figures / "confusion_matrix_test.png",
            figures / "confusion_matrix_val.png",
            figures / "confusion_matrix_test.jpg",
            figures / "confusion_matrix_val.jpg",
        ]
    )


def resolve_failure_case_images(
    paths: dict[str, Path] | None = None,
    limit: int = 4,
) -> list[Path]:
    """Return up to *limit* failure-case thumbnails."""
    p = paths or _resolved_paths()
    failures_dir = p.get("figures_dir", PROJECT_ROOT / "artifacts/figures") / "failures"
    if not failures_dir.exists():
        return []
    images = sorted(failures_dir.glob("*.png")) + sorted(failures_dir.glob("*.jpg"))
    return images[:limit]


def resolve_image_path(relative_path: str) -> Path | None:
    """Resolve a repo-relative image path, returning ``None`` if missing."""
    if not relative_path:
        return None
    path = PROJECT_ROOT / relative_path
    return path if path.exists() else None


def scene_local_image_paths(scene: dict[str, Any]) -> tuple[Path | None, Path | None]:
    """Resolve local pre/post disaster image paths for a scene record."""
    pre_path = resolve_image_path(scene.get("pre_image_path", ""))
    post_path = resolve_image_path(scene.get("post_image_path", ""))
    return pre_path, post_path


def scene_has_local_images(scene: dict[str, Any]) -> bool:
    """Return True when both pre- and post-disaster images exist on disk."""
    pre_path, post_path = scene_local_image_paths(scene)
    return pre_path is not None and post_path is not None


def prioritize_scene_ids(
    scenes: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    prediction_scene_ids: set[str] | None = None,
) -> list[str]:
    """Order scenes so cached predictions and local imagery appear first."""
    scene_by_id = {str(scene["scene_id"]): scene for scene in scenes if scene.get("scene_id")}
    summary_by_id = {
        str(summary["scene_id"]): summary for summary in summaries if summary.get("scene_id")
    }
    ordered_ids = list(dict.fromkeys(list(summary_by_id) + list(scene_by_id)))

    def sort_key(scene_id: str) -> tuple[int, int, float]:
        has_predictions = 1 if prediction_scene_ids and scene_id in prediction_scene_ids else 0
        scene = scene_by_id.get(scene_id, {})
        has_images = 1 if scene_has_local_images(scene) else 0
        priority = float(summary_by_id.get(scene_id, {}).get("priority_score", 0))
        return (has_predictions + has_images, has_predictions, priority)

    return sorted(ordered_ids, key=sort_key, reverse=True)


def build_report_csv(summary: dict[str, Any], predictions: list[dict[str, Any]]) -> str:
    """Render a scene report as a CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "value"])
    for key, value in summary.items():
        if key != "class_counts":
            writer.writerow(["summary", key, value])
    for label, count in summary.get("class_counts", {}).items():
        writer.writerow(["class_count", label, count])
    for pred in predictions:
        writer.writerow(
            [
                "prediction",
                pred.get("building_id", ""),
                pred.get("predicted_label", ""),
                pred.get("confidence", ""),
                pred.get("needs_review", ""),
            ]
        )
    return buf.getvalue()


def _sort_by_priority(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda r: r.get("priority_score", 0), reverse=True)
