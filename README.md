# DisasterSight

DisasterSight is a local-first Streamlit dashboard project for AI-assisted satellite damage triage using xBD/xView2 pre-disaster and post-disaster imagery.

The current baseline deliberately uses xBD-provided building polygons for localisation first. It does not train or run a segmentation model yet. This keeps the MVP reliable, testable, and aligned with the MDN proposal's must-have scope.

DisasterSight is an academic decision-support prototype for human review. It is not an operational emergency-response or dispatch system.

## MVP Pipeline

1. Load an xBD/xView2 subset and pair pre/post scenes.
2. Parse xBD building polygons and damage labels.
3. Build event-aware train/validation/test scene manifests.
4. Extract paired pre/post building crops from xBD polygons.
5. Train a simple paired-crop damage classifier.
6. Cache predictions for demo scenes.
7. Display overlays, severity counts, priority score, confidence, review flags, and model evaluation in Streamlit.

## Current Status

Implemented:

- Config-driven project paths.
- xBD scene discovery and pre/post pairing.
- xBD annotation parsing for building polygons, bounding boxes, and canonical labels.
- Event-aware scene manifest generation.
- Deterministic small-subset scene manifests for controlled experiments.
- Paired pre/post crop extraction with crop manifest output.
- Crop manifest validation and QA contact-sheet generation.
- Focused unit tests for parsing, manifests, crop extraction, and manifest validation.
- Baseline paired-crop classifier training and evaluation scripts.
- Cached building prediction and scene-summary generation for dashboard use.
- Real artifact resolution for scene manifests, cached predictions, metrics, and confusion matrices.

- Streamlit dashboard with three pages (Dashboard, Map Explorer, Analytics).
- Pure artifact-resolver layer decoupled from Streamlit for testability.
- Demo fixtures for offline development when artifacts are not yet generated.
- Dashboard unit tests for labels, priority, overlays, and artifact resolution.

## Scope Control

Included for this MVP:

- xBD/xView2 as the primary dataset.
- xBD polygon-based building localisation.
- Simple paired-crop damage classification.
- Cached local demo outputs.
- Streamlit-first dashboard.
- Responsible-AI framing and human review flags.

Explicitly out of scope unless requested:

- U-Net or other segmentation models.
- SpaceNet 8 roads/flooding.
- FastAPI backend.
- React frontend.
- Live satellite ingestion.
- Cloud deployment.
- Route optimisation.
- Production emergency-response claims.

## Repository Layout

```text
DisasterSight/
  config.yaml
  .streamlit/config.toml
  data/
    README.md
  docs/
    artifacts_integration.md
    design_system.md
    foundation_guardrails.md
    implementation_plan.md
    interface_contracts.md
  src/
    common/
      constants.py
      paths.py
    data/
      build_crop_manifest.py
      build_scene_manifest.py
      crop_extraction.py
      xbd.py
    dashboard/
      app.py                  # Streamlit entry-point
      artifact_resolver.py    # Pure I/O, no Streamlit dependency
      config.py               # Config accessors
      data_loaders.py         # Streamlit-cached facade
      labels.py               # Label normalization
      navigation.py           # Page navigation
      overlays.py             # Image overlay drawing
      priority.py             # Priority score computation
      styles.py               # Theme injection
      components/             # Reusable UI components
      fixtures/               # Demo data for offline dev
      pages/                  # Multi-page scripts
    inference/
      generate_predictions.py
    models/
      train.py
      evaluate.py
  tests/
    test_xbd.py
    test_dashboard.py
    test_inference.py
  README.md
  requirements.txt
```

Generated local outputs are ignored by git:

```text
data/raw/
data/interim/
data/processed/
data/cache/
artifacts/
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Place xBD files under the configured `paths.xbd_root` in `config.yaml`. By default, that is `data/raw/xbd`.

## Run Order

Build the scene manifest:

```powershell
python -m src.data.build_scene_manifest
```

The default config uses a deterministic three-event subset that keeps events
whole while still producing train/validation/test splits. To build the full
local manifest, run:

```powershell
python -m src.data.build_scene_manifest --all-scenes --output-name scene_manifest_full.csv
```

Extract paired building crops:

```powershell
python -m src.data.build_crop_manifest
```

Optionally save masked crops for QA:

```powershell
python -m src.data.build_crop_manifest --save-masked
```

Validate the generated crop manifest and create a quick visual QA preview:

```powershell
python -m src.data.validate_crop_manifest
python -m src.data.build_crop_qa_preview
```

Preview a wildfire scene after creating the wildfire index:

```powershell
python -m src.data.find_wildfire_events
python -m src.data.preview_xbd_scene --scene-id pinery-bushfire_00000000
```

Summarise wildfire label coverage:

```powershell
python -m src.data.summarise_wildfire_labels
```

Train, evaluate, then cache dashboard-ready predictions:

```powershell
python -m src.models.train
python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt --save-figure
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/best_classifier.pt
```

On CPU-only machines, use bounded class-aware samples for a quick real-data
smoke run without falling back to fixtures:

```powershell
python -m src.models.train --manifest artifacts/manifests/crop_manifest_small.csv --max-epochs 1 --batch-size 16 --image-size 64 --num-workers 0 --max-train-samples 128 --max-val-samples 64 --no-pretrained
python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt --manifest artifacts/manifests/crop_manifest_small.csv --split test --batch-size 16 --num-workers 0 --max-samples 128 --save-figure
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/best_classifier.pt --manifest artifacts/manifests/crop_manifest_small.csv --split test --scene-limit 5 --batch-size 16 --num-workers 0
```

The prediction cache writes CSV artifacts under `artifacts/predictions/`:

- `building_predictions_test.csv`: building-level labels, confidence, class probabilities, overlay geometry, and review flags.
- `scene_summaries_test.csv`: severity counts, priority score, mean confidence, and review flag counts.
- `artifacts/metrics.json` and `artifacts/figures/confusion_matrix_test.png`: dashboard evaluation metrics and confusion matrix.

Launch the dashboard:

```powershell
streamlit run src/dashboard/app.py
```

The dashboard loads cached artifacts from `artifacts/` and `data/processed/`.
When artifacts are not yet generated, demo fixtures provide placeholder data.

## Quality Checks

```powershell
python -m ruff check .
python -m unittest discover -s tests
python -m compileall -q src tests
```

Before adding a new phase, review `docs/foundation_guardrails.md` and update
`docs/interface_contracts.md` when a module boundary or output schema changes.
