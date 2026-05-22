"""Shared evaluation-to-dashboard metrics formatting."""

from __future__ import annotations

from typing import Any

from src.common.constants import DAMAGE_CLASSES


def normalize_confusion_matrix(
    cm_data: dict[str, Any] | list[list[float]],
) -> tuple[list[list[float]], list[str]]:
    """Return row-normalized matrix and class labels for dashboard display."""
    if isinstance(cm_data, dict):
        matrix = cm_data.get("matrix", [])
        labels = cm_data.get("classes", list(DAMAGE_CLASSES))
    else:
        matrix = cm_data
        labels = list(DAMAGE_CLASSES)

    norm_matrix: list[list[float]] = []
    for cm_row in matrix:
        row_sum = sum(cm_row)
        if row_sum > 0:
            norm_matrix.append([round(value / row_sum, 4) for value in cm_row])
        else:
            norm_matrix.append([0.0] * len(cm_row))
    return norm_matrix, labels


def format_dashboard_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert evaluate.py output or pre-formatted metrics to dashboard schema."""
    cm_data = raw.get("confusion_matrix", {})
    if isinstance(cm_data, dict) and "matrix" in cm_data:
        norm_matrix, labels = normalize_confusion_matrix(cm_data)
    elif isinstance(cm_data, list):
        norm_matrix = cm_data
        labels = raw.get("confusion_labels", list(DAMAGE_CLASSES))
    else:
        norm_matrix, labels = normalize_confusion_matrix({})

    return {
        "macro_f1": round(float(raw.get("macro_f1", 0.0)), 3),
        "macro_f1_delta": float(raw.get("macro_f1_delta", 0.0)),
        "precision_macro": round(float(raw.get("precision_macro", 0.0)), 3),
        "precision_label": raw.get("precision_label", "Live"),
        "recall_macro": round(float(raw.get("recall_macro", 0.0)), 3),
        "recall_delta": float(raw.get("recall_delta", 0.0)),
        "held_out_events": int(raw.get("held_out_events", 0)),
        "confusion_matrix": norm_matrix,
        "confusion_labels": labels,
        "validation_patches": int(raw.get("num_samples", raw.get("validation_patches", 0))),
        "per_class_f1": raw.get("per_class_f1", {}),
        "mean_confidence": float(raw.get("mean_confidence", 0.0)),
    }
