# Artifacts Integration

The dashboard resolves team outputs through the pure layer
`src/dashboard/artifact_resolver.py` (no Streamlit dependency). The thin
Streamlit facade in `src/dashboard/data_loaders.py` adds caching and
fixture-fallback warnings.

## Resolution order

| Artifact | Primary paths | Inference pipeline fallback | Offline fallback |
|---|---|---|---|
| Scene manifest | `data/processed/scenes.json`, `artifacts/manifests/scenes.json` | `artifacts/manifests/scene_manifest.csv` | `src/dashboard/fixtures/demo_scenes.json` |
| Zone summaries | `artifacts/zone_summaries.json`, `data/processed/zone_summaries.json` | `artifacts/predictions/scene_summaries_{split}.csv` | `src/dashboard/fixtures/demo_zone_summaries.json` |
| Building predictions | `artifacts/predictions/{scene_id}.json`, `.jsonl`, `predictions.parquet` | `artifacts/predictions/building_predictions_{split}.csv` | `src/dashboard/fixtures/demo_predictions.jsonl` |
| Metrics | `artifacts/metrics.json`, `artifacts/figures/metrics.json` | `artifacts/figures/eval_results_{split}.json` | `src/dashboard/fixtures/demo_metrics.json` |
| Confusion matrix image | `artifacts/figures/confusion_matrix_{split}.png` | — | Heatmap from normalized matrix JSON |
| Failure cases | `artifacts/figures/failures/*.png` | — | Placeholder info card |

Missing real artifacts trigger demo fixtures with a one-time Streamlit warning per session (scenes, summaries, metrics, and predictions).

Remote preview URLs and synthetic demo overlays are not used. Scene Explorer reads local xBD imagery from manifest paths only. Damage overlays require real bbox fields from cached inference CSVs.

Scene Explorer pane height auto-adapts to the computed slot width so square images fill the container without dead-space padding. An explicit cap can be set via `dashboard.scene_explorer_max_pane_height_px` in `config.yaml` if needed. Layout sizing is computed in `scene_viewer_layout.py`; interactive zoom/pan and full-width viewing are implemented in `src/dashboard/components/scene_viewer/assets/viewer.js`.

`python -m src.models.evaluate` always writes `artifacts/metrics.json` in dashboard format; pass `--save-figure` to also emit the confusion-matrix PNG.

## Cache behavior

Dashboard data loaders use `st.cache_data` only for file-backed artifacts. Each
cached call is keyed by `config.yaml` plus the relevant artifact file paths,
modification times, and file sizes, so replacing predictions, metrics, scene
manifests, or summary files invalidates the matching cache on the next rerun.
The sidebar also exposes a "Refresh cached artifacts" action for manual local
development resets.

Theme CSS is refreshed by content hash in `src/dashboard/styles.py`; changes to
`src/dashboard/theme.css` replace the existing injected style block during the
same Streamlit browser session instead of waiting for a hard refresh.

## Pipeline outputs that feed the dashboard

After training and evaluation:

```powershell
python -m src.models.train
python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt --save-figure
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/best_classifier.pt
```

For CPU-only local smoke runs against the real xBD crop manifest, use bounded
class-aware samples:

```powershell
python -m src.models.train --manifest artifacts/manifests/crop_manifest_small.csv --max-epochs 1 --batch-size 16 --image-size 64 --num-workers 0 --max-train-samples 128 --max-val-samples 64 --no-pretrained
python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt --manifest artifacts/manifests/crop_manifest_small.csv --split test --batch-size 16 --num-workers 0 --max-samples 128 --save-figure
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/best_classifier.pt --manifest artifacts/manifests/crop_manifest_small.csv --split test --scene-limit 5 --batch-size 16 --num-workers 0
```

This writes:

- `artifacts/metrics.json` — macro F1, per-class F1, normalized confusion matrix
- `artifacts/figures/confusion_matrix_test.png` — confusion matrix figure
- `artifacts/predictions/building_predictions_test.csv` — building-level predictions with bbox overlay fields
- `artifacts/predictions/scene_summaries_test.csv` — zone summaries with priority scores

All paths are config-driven via `config.yaml`; no absolute machine paths.
