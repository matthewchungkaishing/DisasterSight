# Artifacts Integration

The dashboard loads team outputs from these paths (see `src/dashboard/data_loaders.py`):

| Path | Used for |
|------|----------|
| `artifacts/predictions/{scene_id}.json` | Building predictions |
| `artifacts/zone_summaries.json` | Map Explorer priority table |
| `artifacts/metrics.json` | Analytics macro metrics |
| `artifacts/figures/confusion_matrix.png` | Confusion matrix image |
| `artifacts/figures/failures/*.png` | Failure-case thumbnails |
| `data/processed/scenes.json` | Scene manifest |
| `artifacts/manifests/scenes.json` | Alternate scene manifest |

Missing files trigger demo fixtures under `src/dashboard/fixtures/` with a Streamlit warning.
