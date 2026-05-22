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
- Paired pre/post crop extraction with crop manifest output.
- Focused unit tests for parsing, manifests, and crop extraction.

Next:

- Crop QA previews and metadata validation.
- Baseline paired-image classifier.
- Macro F1 and confusion matrix evaluation.
- Cached prediction generation.
- Streamlit dashboard integration.

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
  data/
    README.md
  docs/
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
  tests/
    test_xbd.py
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
outputs/
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

Extract paired building crops:

```powershell
python -m src.data.build_crop_manifest
```

Optionally save masked crops for QA:

```powershell
python -m src.data.build_crop_manifest --save-masked
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

## Quality Checks

```powershell
python -m ruff check .
python -m unittest discover -s tests
python -m compileall -q src tests
```
