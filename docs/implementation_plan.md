# Implementation Plan

## Objective

Build a local MVP that uses xBD building polygons to support building-level damage triage in a Streamlit dashboard. Keep the pipeline simple, cached, and reproducible.

## Phase 0: Repository Scaffold

Status: complete after this task.

Deliverables:
- Project README
- Dependency list
- Central config
- Shared constants and path helpers
- Interface and implementation planning docs

## Phase 0.5: Foundation Hardening

Status: complete.

Deliverables:
- `data/README.md` with local data policy and expected layout
- Shared xBD parser for scene pairing, annotation parsing, and label normalization
- Reusable scene manifest helpers with event-aware splitting
- Focused parser and manifest tests

Success criteria:
- Exploratory scripts use shared parsing code.
- Labels use canonical config names such as `no_damage` and `major_damage`.
- A general xBD scene manifest can be generated from config only.

## Phase 1: Data Layout and xBD Parsing

Status: complete.

Deliverables:
- `data/README.md`
- Expected raw-data folder structure for xBD
- xBD metadata parser for pre/post image pairs
- Building polygon and damage label extraction
- Train/val/test manifests with event-aware splitting

Success criteria:
- A small subset can be indexed locally.
- Scene-level records are reproducible from config only.

## Phase 2: Building Crop Extraction

Status: complete.

Deliverables:
- Polygon-to-bounding-box crop extraction
- Paired pre/post building crops
- Optional masked crops for debugging
- Cached crop metadata CSV or Parquet

Success criteria:
- Each crop record maps back to scene, building id, polygon, and label.
- A small sample can be visualized for QA.

## Phase 3: Baseline Damage Classifier

Status: next.

Deliverables:
- Simple paired-image classifier baseline
- Training script with config-driven hyperparameters
- Validation metrics: macro F1, confusion matrix
- Small local checkpoint and training logs

Success criteria:
- End-to-end training runs on a subset.
- Inference outputs include class probabilities and confidence.

## Phase 4: Cached Inference Outputs

Deliverables:
- Prediction generation script for demo scenes
- Zone/building-level cached outputs
- Review-required flag logic
- Priority score computation

Success criteria:
- Streamlit can load predictions without running the model live.
- Cached outputs are stable enough for demo use.

## Phase 5: Streamlit Dashboard

Deliverables:
- Scene selector
- Pre/post image viewer
- Damage overlay toggle
- Severity counts
- Priority score panel
- Confidence and review flags
- Evaluation panel with confusion matrix and limitations

Success criteria:
- The main demo flow is understandable in under two minutes.
- The app clearly presents responsible-AI limitations.

## Non-Goals For This MVP

- U-Net or other segmentation implementation
- SpaceNet 8 roads/flooding integration
- FastAPI backend
- React frontend
- Live satellite ingestion
- Production emergency-response claims

## Risks and Controls

- Large dataset size:
  Use a small event-aware subset first.
- Weak four-class performance:
  Be prepared to collapse to three-class or binary damage labels later.
- Demo instability:
  Prefer cached inference outputs and backup screenshots.
