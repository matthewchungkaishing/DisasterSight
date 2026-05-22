from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.common.paths import PROJECT_ROOT
from src.dashboard.config import FIXTURES_DIR, get_paths
from src.dashboard.labels import normalize_label
from src.dashboard.priority import build_zone_summary

_USING_FIXTURES_KEY = "_ds_using_fixtures"


def _warn_fixtures(message: str) -> None:
    st.session_state[_USING_FIXTURES_KEY] = True
    if message not in st.session_state.get("_ds_fixture_messages", []):
        st.session_state.setdefault("_ds_fixture_messages", []).append(message)
        st.warning(message)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@st.cache_data(show_spinner=False)
def load_scenes() -> list[dict[str, Any]]:
    """Load scene records: processed manifest, then fixtures."""
    paths = get_paths()
    candidates = [
        paths.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "scenes.json",
        paths.get("manifests_dir", PROJECT_ROOT / "artifacts/manifests") / "scenes.json",
        paths.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "scenes.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            if candidate.suffix == ".csv":
                df = pd.read_csv(candidate)
                return df.to_dict(orient="records")
            data = _load_json(candidate)
            if isinstance(data, list):
                return data
    _warn_fixtures("Using demo scene fixtures — place manifests under data/processed/ or artifacts/manifests/.")
    return _load_json(FIXTURES_DIR / "demo_scenes.json")


@st.cache_data(show_spinner=False)
def load_zone_summaries() -> list[dict[str, Any]]:
    """Load zone summaries for priority ranking."""
    paths = get_paths()
    candidates = [
        paths.get("artifacts_dir", PROJECT_ROOT / "artifacts") / "zone_summaries.json",
        paths.get("processed_data_dir", PROJECT_ROOT / "data/processed") / "zone_summaries.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            data = _load_json(candidate)
            if isinstance(data, list):
                return sorted(data, key=lambda x: x.get("priority_score", 0), reverse=True)
    _warn_fixtures("Using demo zone summaries — team outputs can be written to artifacts/zone_summaries.json.")
    data = _load_json(FIXTURES_DIR / "demo_zone_summaries.json")
    return sorted(data, key=lambda x: x.get("priority_score", 0), reverse=True)


@st.cache_data(show_spinner=False)
def load_predictions(scene_id: str) -> list[dict[str, Any]]:
    """Load building-level predictions for a scene."""
    paths = get_paths()
    pred_dir = paths.get("predictions_dir", PROJECT_ROOT / "artifacts/predictions")
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
            df = df[df["scene_id"] == scene_id] if "scene_id" in df.columns else df
            return df.to_dict(orient="records")
        if candidate.suffix == ".jsonl":
            rows = [r for r in _load_jsonl(candidate) if r.get("scene_id") == scene_id]
            if rows:
                return rows
        else:
            data = _load_json(candidate)
            if isinstance(data, list):
                return [r for r in data if r.get("scene_id") == scene_id]
            if isinstance(data, dict) and "predictions" in data:
                return [r for r in data["predictions"] if r.get("scene_id") == scene_id]
    rows = [r for r in _load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl") if r.get("scene_id") == scene_id]
    if not rows and scene_id != "pinery-bushfire_00000000":
        rows = [r for r in _load_jsonl(FIXTURES_DIR / "demo_predictions.jsonl")]
    return rows


def get_zone_summary_for_scene(scene_id: str) -> dict[str, Any]:
    """Zone summary for one scene, computing from predictions if needed."""
    for summary in load_zone_summaries():
        if summary.get("scene_id") == scene_id:
            return summary
    predictions = load_predictions(scene_id)
    class_counts: dict[str, int] = {}
    review_count = 0
    for pred in predictions:
        label = normalize_label(pred.get("predicted_label", "unknown"))
        if pred.get("needs_review"):
            review_count += 1
        class_counts[label] = class_counts.get(label, 0) + 1
    return build_zone_summary(scene_id, class_counts, review_count)


def get_scene_by_id(scene_id: str) -> dict[str, Any] | None:
    for scene in load_scenes():
        if scene.get("scene_id") == scene_id:
            return scene
    return None


def resolve_image_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
    path = PROJECT_ROOT / relative_path
    return path if path.exists() else None


def get_scene_image_sources(scene: dict[str, Any]) -> tuple[str | None, str | None, Path | None, Path | None]:
    """Return pre/post demo URLs (Stitch) and local paths if available."""
    pre_url = scene.get("pre_image_url") or None
    post_url = scene.get("post_image_url") or None
    pre_path = resolve_image_path(scene.get("pre_image_path", ""))
    post_path = resolve_image_path(scene.get("post_image_path", ""))
    if pre_path and post_path:
        return None, None, pre_path, post_path
    return pre_url, post_url, pre_path, post_path


@st.cache_data(show_spinner=False)
def load_metrics() -> dict[str, Any]:
    """Evaluation metrics for Analytics page."""
    paths = get_paths()
    candidates = [
        paths.get("artifacts_dir", PROJECT_ROOT / "artifacts") / "metrics.json",
        paths.get("figures_dir", PROJECT_ROOT / "artifacts/figures") / "metrics.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return _load_json(candidate)
    return _load_json(FIXTURES_DIR / "demo_metrics.json")


def confusion_matrix_image_path() -> Path | None:
    paths = get_paths()
    figures = paths.get("figures_dir", PROJECT_ROOT / "artifacts/figures")
    for name in ("confusion_matrix.png", "confusion_matrix.jpg"):
        path = figures / name
        if path.exists():
            return path
    return None


def failure_case_images() -> list[Path]:
    paths = get_paths()
    failures_dir = paths.get("figures_dir", PROJECT_ROOT / "artifacts/figures") / "failures"
    if failures_dir.exists():
        images = sorted(failures_dir.glob("*.png")) + sorted(failures_dir.glob("*.jpg"))
        if images:
            return images[:4]
    return []


def export_report_csv(scene_id: str) -> str:
    """Build CSV export for current scene."""
    summary = get_zone_summary_for_scene(scene_id)
    predictions = load_predictions(scene_id)
    lines = ["section,key,value"]
    for key, value in summary.items():
        if key != "class_counts":
            lines.append(f"summary,{key},{value}")
    for label, count in summary.get("class_counts", {}).items():
        lines.append(f"class_count,{label},{count}")
    for pred in predictions:
        lines.append(
            f"prediction,{pred.get('building_id')},{pred.get('predicted_label')},"
            f"{pred.get('confidence')},{pred.get('needs_review')}"
        )
    return "\n".join(lines)
