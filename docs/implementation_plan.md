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

Status: complete, with validation gate added.

Deliverables:
- Polygon-to-bounding-box crop extraction
- Paired pre/post building crops
- Optional masked crops for debugging
- Cached crop metadata CSV or Parquet
- Crop manifest validation command
- Crop QA preview contact sheet

Success criteria:
- Each crop record maps back to scene, building id, polygon, and label.
- A small sample can be visualized for QA.
- The crop manifest passes schema, path, label, split, and bbox validation.

## Phase 3: Baseline Damage Classifier

Status: complete — model package, training script, evaluation script, and dashboard metrics export implemented.

Deliverables:
- Simple paired-image classifier baseline (ResNet-18, 6-channel pre+post input)
- Training script with config-driven hyperparameters (`src/models/train.py`)
- Evaluation script with macro F1, per-class F1, confusion matrix (`src/models/evaluate.py`)
- Small local checkpoint and training logs under `artifacts/checkpoints/`
- Confusion matrix figure saved to `artifacts/figures/`

Class-imbalance note:
The validated xBD crop set is heavily imbalanced (minor_damage is significantly
under-represented).  `class_weight_strategy` in `config.yaml` controls how this
is handled: `loss_weight` applies inverse-frequency weights to CrossEntropyLoss,
`sampler` uses WeightedRandomSampler for balanced batches, and `both` combines them.
Default is `loss_weight`.

Success criteria:
- End-to-end training runs on a subset without NaN loss.
- Best checkpoint is saved by highest val macro F1.
- Inference outputs include class probabilities and confidence.
- Confusion matrix JSON and optional PNG are saved for dashboard use.

## Phase 4: Cached Inference Outputs

Status: complete.

Deliverables:
- Prediction generation script for demo scenes (`src/inference/generate_predictions.py`)
- Building-level cached outputs (`artifacts/predictions/building_predictions_{split}.csv`)
- Scene-level summary outputs (`artifacts/predictions/scene_summaries_{split}.csv`)
- Review-required flag logic
- Priority score computation

Success criteria:
- Streamlit can load predictions without running the model live.
- Cached outputs are stable enough for demo use.

## Phase 5: Streamlit Dashboard

Status: complete — artifact resolution hardened for real pipeline outputs.

Architecture:
- Pure artifact resolution layer (`artifact_resolver.py`) decoupled from Streamlit
- Shared domain logic in `src/common/` (`priority_score.py`, `metrics_format.py`)
- Thin Streamlit-cached facade (`data_loaders.py`) with fixture-fallback warnings
- Reusable UI components under `src/dashboard/components/`
- Multi-page navigation via `st.navigation`
- Custom dark theme with Material Design icons

Deliverables:
- Scene selector with sidebar navigation
- Pre/post image viewer with local manifest paths only
- Damage overlay toggle with configurable opacity
- Severity breakdown bars
- Priority score panel with zone summaries
- Confidence and review flags with building-level table
- Map Explorer page with priority ranking and review queue
- Analytics page with confusion matrix and known limitations
- Responsible-AI notices on every page
- CSV export for scene reports
- Demo fixtures for offline development
- Unit tests for all pure-logic modules

Success criteria:
- The main demo flow is understandable in under two minutes.
- The app clearly presents responsible-AI limitations.
- Pure logic is testable without a running Streamlit server.

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
