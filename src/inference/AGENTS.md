# AGENTS.md - src/inference/

## Module Purpose

Cached inference layer for dashboard-ready DisasterSight outputs. This package turns trained classifier outputs into stable CSV artifacts that Streamlit can load without running the model live.

## Key Conventions

- Keep cached predictions building-level and scene-level. Do not introduce a service layer.
- Prediction rows must preserve crop-manifest metadata needed for overlays: `scene_id`, `building_id`, `polygon_xy`, `bbox_*`, and crop paths.
- Review flags are confidence-threshold based and must remain human-in-the-loop.
- Priority scores are demo triage scores only, using `config.yaml` weights.
- Paths should resolve from `config.yaml` and outputs should go under `paths.predictions_dir`.

## What Not To Do

- Do not add FastAPI, React, live inference endpoints, or cloud deployment.
- Do not frame priority scores as dispatch decisions.
- Do not change damage classes locally; import them from `src.common.constants`.

## Testing

- Tests should cover prediction schema, review-flag logic, priority-score aggregation, and CSV writing with temporary files.
