"""Streamlit-cached data access layer.

Thin facade over :mod:`artifact_resolver` that adds ``st.cache_data``
caching and fixture-fallback warnings.  All pure I/O and file-resolution
logic lives in :mod:`artifact_resolver` so it can be tested without
Streamlit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.artifact_resolver import (
    build_report_csv,
    resolve_metrics,
    resolve_predictions,
    resolve_scenes,
    resolve_zone_summaries,
    scene_image_sources,
)
from src.dashboard.labels import normalize_label
from src.dashboard.priority import build_zone_summary

_FIXTURE_MESSAGES_KEY = "_ds_fixture_messages"


def _warn_fixture(message: str) -> None:
    """Show a Streamlit warning once per session for fixture fallbacks."""
    shown: list[str] = st.session_state.setdefault(_FIXTURE_MESSAGES_KEY, [])
    if message not in shown:
        shown.append(message)
        st.warning(message)


@st.cache_data(show_spinner=False)
def load_scenes() -> list[dict[str, Any]]:
    """Cached scene manifest loader with fixture fallback."""
    records, is_fixture = resolve_scenes()
    if is_fixture:
        _warn_fixture(
            "Using demo scene fixtures — place manifests under "
            "data/processed/ or artifacts/manifests/."
        )
    return records


@st.cache_data(show_spinner=False)
def load_zone_summaries() -> list[dict[str, Any]]:
    """Cached zone-summary loader with fixture fallback."""
    records, is_fixture = resolve_zone_summaries()
    if is_fixture:
        _warn_fixture(
            "Using demo zone summaries — team outputs can be written "
            "to artifacts/zone_summaries.json."
        )
    return records


@st.cache_data(show_spinner=False)
def load_predictions(scene_id: str) -> list[dict[str, Any]]:
    """Cached building-prediction loader for a single scene."""
    return resolve_predictions(scene_id)


@st.cache_data(show_spinner=False)
def load_metrics() -> dict[str, Any]:
    """Cached evaluation-metrics loader."""
    metrics, is_fixture = resolve_metrics()
    if is_fixture:
        _warn_fixture(
            "Using demo metrics fixtures — run evaluate with --save-figure "
            "to write artifacts/metrics.json from real model outputs."
        )
    return metrics


def get_scene_by_id(scene_id: str) -> dict[str, Any] | None:
    """Look up a single scene record by ID."""
    scene: dict[str, Any]
    for scene in load_scenes():
        if scene.get("scene_id") == scene_id:
            return scene
    return None


def get_zone_summary_for_scene(scene_id: str) -> dict[str, Any]:
    """Return zone summary for *scene_id*, computing on-the-fly if needed."""
    summary: dict[str, Any]
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


def get_scene_image_sources(
    scene: dict[str, Any],
) -> tuple[str | None, str | None, Path | None, Path | None]:
    """Delegate to pure resolver; kept for backward compatibility."""
    return scene_image_sources(scene)


def export_report_csv(scene_id: str) -> str:
    """Build a downloadable CSV report for the given scene."""
    summary = get_zone_summary_for_scene(scene_id)
    predictions = load_predictions(scene_id)
    return build_report_csv(summary, predictions)
