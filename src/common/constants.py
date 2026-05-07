from __future__ import annotations


PROJECT_NAME = "DisasterSight"
DATASET_NAME = "xBD / xView2"

MVP_SCOPE_EXCLUSIONS = (
    "segmentation_model",
    "spacenet8_accessibility",
    "fastapi_backend",
    "react_frontend",
    "live_satellite_ingestion",
)

DAMAGE_CLASSES = (
    "no_damage",
    "minor_damage",
    "major_damage",
    "destroyed",
)

CLASS_TO_INDEX = {label: idx for idx, label in enumerate(DAMAGE_CLASSES)}
INDEX_TO_CLASS = {idx: label for label, idx in CLASS_TO_INDEX.items()}

OVERLAY_COLORS = {
    "no_damage": "#4CAF50",
    "minor_damage": "#FFC107",
    "major_damage": "#FF7043",
    "destroyed": "#C62828",
    "review_required": "#42A5F5",
}

PRIMARY_METRICS = (
    "macro_f1",
    "precision_macro",
    "recall_macro",
    "confusion_matrix",
)

REVIEW_REQUIRED_LABEL = "review_required"

PRIORITY_SCORE_FORMULA = (
    "100 * (0.50 * destroyed_share + 0.30 * major_damage_share + "
    "0.20 * damage_density)"
)
