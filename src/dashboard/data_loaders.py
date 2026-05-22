"""Streamlit-cached data access layer with artifact-aware invalidation."""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from src.common.paths import CONFIG_PATH, get_path_map
from src.dashboard.artifact_resolver import (
    build_report_csv,
    prioritize_scene_ids,
    resolve_metrics,
    resolve_prediction_scene_ids,
    resolve_predictions,
    resolve_scenes,
    resolve_zone_summaries,
    scene_local_image_paths,
)
from src.dashboard.labels import normalize_label
from src.dashboard.priority import build_zone_summary

_FIXTURE_MESSAGES_KEY = "_ds_fixture_messages"
_CACHE_MAX_ENTRIES = 32


def _file_token(path) -> tuple[str, int, int] | tuple[str, int, int, str]:
    """Return a stable token for cache invalidation."""
    if not path.exists():
        return (str(path), 0, 0, "missing")
    stat = path.stat()
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _artifact_token(kind: str, scene_id: str | None = None) -> tuple:
    """Invalidate Streamlit caches when real artifacts appear or change."""
    paths = get_path_map()
    manifests = paths["manifests_dir"]
    predictions = paths["predictions_dir"]
    figures = paths["figures_dir"]
    artifacts = paths["artifacts_dir"]
    processed = paths["processed_data_dir"]

    if kind == "scenes":
        candidates = [
            processed / "scenes.json",
            processed / "scenes.csv",
            manifests / "scenes.json",
            manifests / "scene_manifest.csv",
            manifests / "scene_manifest_small.csv",
        ]
    elif kind == "summaries":
        candidates = [
            artifacts / "zone_summaries.json",
            processed / "zone_summaries.json",
            *sorted(predictions.glob("scene_summaries_*.csv")),
        ]
    elif kind == "metrics":
        candidates = [
            artifacts / "metrics.json",
            figures / "metrics.json",
            *sorted(figures.glob("eval_results_*.json")),
        ]
    elif kind == "predictions":
        candidates = [
            predictions / f"{scene_id}.json",
            predictions / f"{scene_id}.jsonl",
            predictions / "predictions.parquet",
            *sorted(predictions.glob("building_predictions_*.csv")),
        ]
    elif kind == "prediction_scenes":
        candidates = sorted(predictions.glob("building_predictions_*.csv"))
    else:
        candidates = []
    return (_file_token(CONFIG_PATH), *(_file_token(path) for path in candidates))


def _warn_fixture(message: str) -> None:
    """Show a Streamlit warning once per session for fixture fallbacks."""
    shown: list[str] = st.session_state.setdefault(_FIXTURE_MESSAGES_KEY, [])
    if message not in shown:
        shown.append(message)
        st.warning(message)


@st.cache_data(show_spinner=False, max_entries=_CACHE_MAX_ENTRIES)
def _load_scenes_cached(token: tuple) -> tuple[list[dict[str, Any]], bool]:
    """Cached scene loader keyed by artifact/config file metadata."""
    return resolve_scenes()


def load_scenes() -> list[dict[str, Any]]:
    """Scene manifest loader with artifact-aware cache invalidation."""
    records, is_fixture = _load_scenes_cached(_artifact_token("scenes"))
    if is_fixture:
        _warn_fixture(
            "Using demo scene fixtures - place manifests under "
            "data/processed/ or artifacts/manifests/."
        )
    return cast(list[dict[str, Any]], records)


@st.cache_data(show_spinner=False, max_entries=_CACHE_MAX_ENTRIES)
def _load_zone_summaries_cached(token: tuple) -> tuple[list[dict[str, Any]], bool]:
    """Cached zone-summary loader keyed by artifact/config file metadata."""
    return resolve_zone_summaries()


def load_zone_summaries() -> list[dict[str, Any]]:
    """Zone-summary loader with artifact-aware cache invalidation."""
    records, is_fixture = _load_zone_summaries_cached(_artifact_token("summaries"))
    if is_fixture:
        _warn_fixture(
            "Using demo zone summaries - run cached inference to write "
            "artifacts/predictions/scene_summaries_test.csv."
        )
    return cast(list[dict[str, Any]], records)


@st.cache_data(show_spinner=False, max_entries=_CACHE_MAX_ENTRIES)
def _load_predictions_cached(scene_id: str, token: tuple) -> tuple[list[dict[str, Any]], bool]:
    """Cached prediction loader keyed by scene and artifact/config file metadata."""
    return resolve_predictions(scene_id)


def load_predictions(scene_id: str) -> list[dict[str, Any]]:
    """Building-prediction loader with artifact-aware cache invalidation."""
    records, is_fixture = _load_predictions_cached(
        scene_id, _artifact_token("predictions", scene_id)
    )
    if is_fixture and records:
        _warn_fixture(
            "Using demo prediction fixtures - run generate_predictions to write "
            "artifacts/predictions/building_predictions_test.csv from real xBD crops."
        )
    return cast(list[dict[str, Any]], records)


@st.cache_data(show_spinner=False, max_entries=_CACHE_MAX_ENTRIES)
def _load_prediction_scene_ids_cached(token: tuple) -> set[str]:
    """Cached set of scene IDs with cached predictions."""
    return resolve_prediction_scene_ids()


def load_prediction_scene_ids() -> set[str]:
    """Scene IDs present in cached prediction artifacts."""
    return cast(set[str], _load_prediction_scene_ids_cached(_artifact_token("prediction_scenes")))


@st.cache_data(show_spinner=False, max_entries=_CACHE_MAX_ENTRIES)
def _load_metrics_cached(token: tuple) -> tuple[dict[str, Any], bool]:
    """Cached metrics loader keyed by artifact/config file metadata."""
    return resolve_metrics()


def load_metrics() -> dict[str, Any]:
    """Evaluation-metrics loader with artifact-aware cache invalidation."""
    metrics, is_fixture = _load_metrics_cached(_artifact_token("metrics"))
    if is_fixture:
        _warn_fixture(
            "Using demo metrics fixtures - run evaluate to write "
            "artifacts/metrics.json from real model outputs."
        )
    return cast(dict[str, Any], metrics)


def clear_dashboard_caches() -> None:
    """Clear dashboard-owned Streamlit data caches."""
    _load_scenes_cached.clear()
    _load_zone_summaries_cached.clear()
    _load_predictions_cached.clear()
    _load_prediction_scene_ids_cached.clear()
    _load_metrics_cached.clear()


def load_scene_ids() -> list[str]:
    """Scene IDs ordered for dashboard selection (predictions + imagery first)."""
    return prioritize_scene_ids(
        load_scenes(),
        load_zone_summaries(),
        load_prediction_scene_ids(),
    )


def resolve_selected_scene_id(preferred: str | None = None) -> str:
    """Pick a dashboard scene ID, preferring *preferred* when it has predictions.

    Falls back to the first scene with cached predictions, then the first
    known scene ID. Call before rendering the sidebar so the selector matches
    page content on the same rerun.
    """
    scene_ids = load_scene_ids()
    if not scene_ids:
        return preferred or ""

    selected = preferred if preferred in scene_ids else scene_ids[0]
    if load_predictions(selected):
        return selected

    for candidate_id in scene_ids:
        if load_predictions(candidate_id):
            return candidate_id

    return selected


def get_scene_by_id(scene_id: str) -> dict[str, Any] | None:
    """Look up a single scene record by ID."""
    for scene in load_scenes():
        if scene.get("scene_id") == scene_id:
            return scene
    return None


def get_zone_summary_for_scene(scene_id: str) -> dict[str, Any]:
    """Return zone summary for *scene_id*, computing on-the-fly if needed."""
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


def export_report_csv(scene_id: str) -> str:
    """Build a downloadable CSV report for the given scene."""
    summary = get_zone_summary_for_scene(scene_id)
    predictions = load_predictions(scene_id)
    return build_report_csv(summary, predictions)


def get_scene_image_paths(scene: dict[str, Any]):
    """Return local pre/post image paths for a scene record."""
    return scene_local_image_paths(scene)
