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

from src.common.paths import PROJECT_ROOT, load_config, resolve_path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _resolved_paths() -> dict[str, Path]:
    """Config-driven artifact / data paths, resolved against the repo root."""
    cfg = load_config()
    return {key: resolve_path(val, PROJECT_ROOT) for key, val in cfg.get("paths", {}).items()}


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


def _first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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
    ]
    found = _first_existing(candidates)
    if found is not None:
        if found.suffix == ".csv":
            return pd.read_csv(found).to_dict(orient="records"), False
        data = _load_json(found)
        if isinstance(data, list):
            return data, False
    return _load_json(FIXTURES_DIR / "demo_scenes.json"), True


def resolve_zone_summaries(
    paths: dict[str, Path] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Locate and load zone-level priority summaries."""
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
    fixture = _load_json(FIXTURES_DIR / "demo_zone_summaries.json")
    return _sort_by_priority(fixture), True


def resolve_predictions(
    scene_id: str,
    paths: dict[str, Path] | None = None,
) -> list[dict[str, Any]]:
    """Load building-level predictions for *scene_id*."""
    p = paths or _resolved_paths()
    pred_dir = p.get("predictions_dir", PROJECT_ROOT / "artifacts/predictions")
    candidates = [
        pred_dir / f"{scene_id}.json",
        pred_dir / f"{scene_id}.jsonl",
        pred_dir / "predictions.parquet",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if candidate.suffix == ".parquet":
            df = pd.read_parquet(candidate)
            if "scene_id" in df.columns:
                df = df[df["scene_id"] == scene_id]
            return list(df.to_dict(orient="records"))
        if candidate.suffix == ".jsonl":
            rows = [r for r in _load_jsonl(candidate) if r.get("scene_id") == scene_id]
            if rows:
                return rows
        else:
            data = _load_json(candidate)
            rows = data if isinstance(data, list) else data.get("predictions", [])
            return [r for r in rows if r.get("scene_id") == scene_id]

    fixture = _load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl")
    rows = [r for r in fixture if r.get("scene_id") == scene_id]
    if not rows and scene_id != "pinery-bushfire_00000000":
        rows = list(_load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl"))
    return rows


def resolve_metrics(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    """Load evaluation metrics JSON."""
    p = paths or _resolved_paths()
    candidates = [
        p.get("artifacts_dir", PROJECT_ROOT / "artifacts") / "metrics.json",
        p.get("figures_dir", PROJECT_ROOT / "artifacts/figures") / "metrics.json",
    ]
    found = _first_existing(candidates)
    if found is not None:
        result: dict[str, Any] = _load_json(found)
        return result
    fallback: dict[str, Any] = _load_json(FIXTURES_DIR / "demo_metrics.json")
    return fallback


def resolve_confusion_matrix_image(paths: dict[str, Path] | None = None) -> Path | None:
    """Return the path to a confusion-matrix image if it exists."""
    p = paths or _resolved_paths()
    figures = p.get("figures_dir", PROJECT_ROOT / "artifacts/figures")
    return _first_existing([figures / "confusion_matrix.png", figures / "confusion_matrix.jpg"])


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


def scene_image_sources(
    scene: dict[str, Any],
) -> tuple[str | None, str | None, Path | None, Path | None]:
    """Return ``(pre_url, post_url, pre_path, post_path)`` for a scene.

    When local images are available both URLs are suppressed so the
    dashboard prefers local files.
    """
    pre_url = scene.get("pre_image_url") or None
    post_url = scene.get("post_image_url") or None
    pre_path = resolve_image_path(scene.get("pre_image_path", ""))
    post_path = resolve_image_path(scene.get("post_image_path", ""))
    if pre_path and post_path:
        return None, None, pre_path, post_path
    return pre_url, post_url, pre_path, post_path


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
