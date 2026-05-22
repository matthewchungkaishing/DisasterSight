# DisasterSight

DisasterSight is a local-first Streamlit dashboard for building-level post-disaster damage triage using xBD/xView2 pre-disaster and post-disaster satellite imagery.

The MVP uses xBD-provided building polygons for localisation. It does not train or run a segmentation model yet. The initial pipeline is:

1. Load a small xBD subset and pair pre/post scenes.
2. Parse xBD building polygons and damage labels.
3. Extract building-centered crops from pre/post imagery.
4. Train a simple damage classifier on paired crops.
5. Cache predictions for demo scenes.
6. Visualise overlays, severity counts, priority scores, and review flags in Streamlit.

DisasterSight is an academic decision-support prototype for human review. It is not an operational emergency-response system.

## MVP Scope

Included now:
- xBD/xView2 subset support
- Polygon-based building crop workflow
- Cached local demo outputs
- Streamlit-first dashboard plan
- Evaluation plan using macro F1 and confusion matrix

Explicitly out of scope for this phase:
- U-Net or other building segmentation models
- SpaceNet 8 roads or flooding analysis
- FastAPI or React
- Live satellite APIs
- Production deployment claims

## Repository Layout

```text
DisasterSight/
├── config.yaml
├── docs/
│   ├── implementation_plan.md
│   └── interface_contracts.md
├── src/
│   └── common/
│       ├── constants.py
│       └── paths.py
├── .gitignore
├── README.md
└── requirements.txt
```

Planned future directories:

```text
data/
├── raw/
├── interim/
├── processed/
└── cache/

artifacts/
├── checkpoints/
├── predictions/
└── figures/
```

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Review and adjust local paths in `config.yaml`.

4. When data is available, place xBD files under the configured `data/raw/xbd` directory.

## Next Build Steps

The next implementation milestone is:

1. Finalize xBD scene/building manifests and inspect split quality.
2. Implement polygon-to-crop extraction.
3. Add crop QA previews and metadata validation.
4. Add a baseline paired-image damage classifier.
5. Add cached prediction loading for the Streamlit dashboard.

## Suggested Run Order

After this starter scaffold, the next commands to run are:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

After that, start the first implementation task: dataset folder setup and xBD parsing.

## Scene Manifest

To build a general xBD scene manifest with event-aware train/validation/test splits, run:

```powershell
python -m src.data.build_scene_manifest
```

The script writes `artifacts/manifests/scene_manifest.csv` and uses the split fractions and random seed from `config.yaml`.

## Tests

Run the current foundation tests with:

```powershell
python -m unittest discover -s tests
```

## Wildfire Discovery

If you want to begin with xBD wildfire or bushfire events only, run:

```powershell
python -m src.data.find_wildfire_events
```

The script will:
- scan the configured `data/raw/xbd` tree
- match wildfire-related filenames such as `wildfire`, `woolsey`, `carr`, and `portugal`
- group matching files by scene id
- report whether each scene has pre/post image and JSON files
- save a CSV summary to `data/processed/wildfire_scene_index.csv`
- print the top 10 complete wildfire scenes with all required files

## Scene Preview QA

To visually confirm that xBD pre/post imagery and annotation polygons are loading correctly before any crop generation or model training, run:

```powershell
python -m src.data.preview_xbd_scene --scene-id pinery-bushfire_00000000
```

The script will:
- read `xbd_root` and `processed_data_dir` from `config.yaml`
- load `data/processed/wildfire_scene_index.csv`
- find the pre/post image and JSON files for the requested scene
- print a building-summary report with damage-label counts and sample bounding boxes
- save a QA preview image to `outputs/figures/scene_previews/`

## Wildfire Label Summary

To rank wildfire or bushfire scenes by building-count and damage-label coverage before any crop generation or model training, run:

```powershell
python -m src.data.summarise_wildfire_labels
```

The script will:
- read `xbd_root` and `processed_data_dir` from `config.yaml`
- load `data/processed/wildfire_scene_index.csv`
- parse each complete scene's post-disaster annotation JSON
- count per-scene damage labels and compute damage shares
- save the results to `data/processed/wildfire_label_summary.csv`
- print the top 20 candidate scenes for training selection
