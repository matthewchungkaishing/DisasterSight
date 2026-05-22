# Artifacts Integration

The dashboard resolves team outputs through the pure layer
`src/dashboard/artifact_resolver.py` (no Streamlit dependency). The thin
Streamlit facade in `src/dashboard/data_loaders.py` adds caching and
fixture-fallback warnings.

## Resolution order

| Artifact | Primary paths | Inference pipeline fallback | Offline fallback |
|---|---|---|---|
| Scene manifest | `data/processed/scenes.json`, `artifacts/manifests/scenes.json` | — | `src/dashboard/fixtures/demo_scenes.json` |
| Zone summaries | `artifacts/zone_summaries.json`, `data/processed/zone_summaries.json` | `artifacts/predictions/scene_summaries_{split}.csv` | `src/dashboard/fixtures/demo_zone_summaries.json` |
| Building predictions | `artifacts/predictions/{scene_id}.json`, `.jsonl`, `predictions.parquet` | `artifacts/predictions/building_predictions_{split}.csv` | `src/dashboard/fixtures/demo_predictions.jsonl` |
| Metrics | `artifacts/metrics.json`, `artifacts/figures/metrics.json` | `artifacts/figures/eval_results_{split}.json` | `src/dashboard/fixtures/demo_metrics.json` |
| Confusion matrix image | `artifacts/figures/confusion_matrix_{split}.png` | — | Heatmap from normalized matrix JSON |
| Failure cases | `artifacts/figures/failures/*.png` | — | Placeholder info card |

Missing real artifacts trigger demo fixtures with a one-time Streamlit warning per session.

## Pipeline outputs that feed the dashboard

After training and evaluation:

```powershell
python -m src.models.train
python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt --save-figure
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/best_classifier.pt
```

This writes:

- `artifacts/metrics.json` — macro F1, per-class F1, normalized confusion matrix
- `artifacts/figures/confusion_matrix_test.png` — confusion matrix figure
- `artifacts/predictions/building_predictions_test.csv` — building-level predictions with bbox overlay fields
- `artifacts/predictions/scene_summaries_test.csv` — zone summaries with priority scores

All paths are config-driven via `config.yaml`; no absolute machine paths.
