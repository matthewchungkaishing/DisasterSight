# DisasterSight Model Improvement Plan

## Current proposal coverage

Implemented MVP items:

- xBD/xView2 is the primary dataset.
- xBD building polygons are used for localisation before any learned segmentation.
- Paired pre/post building crops are extracted and tracked through a crop manifest.
- A paired-crop ResNet-18 classifier is trained with macro-F1 early stopping.
- Cached building predictions and scene summaries are generated for Streamlit.
- Dashboard artifacts include overlays, severity counts, priority score, confidence, review flags, macro-F1, and confusion matrix.

Remaining proposal/process items:

- Run and record a full held-out event test evaluation for the promoted checkpoint.
- Add a short failure-case review set for the dashboard or final presentation.
- Keep backup screenshots or a recording for the industry-night demo.
- Decide whether the final story uses 4 classes or reports an additional 3-class/2-class rollup for clearer stakeholder interpretation.

Out of current scope unless explicitly requested:

- U-Net segmentation.
- SpaceNet 8 roads/flooding.
- FastAPI, React, cloud deployment, live imagery, route optimisation, or operational response claims.

## Current model evidence

The old dashboard metric came from a CPU smoke run:

- Checkpoint: `artifacts/checkpoints/best_classifier.pt`
- Config: 1 epoch, 64px crops, no pretrained backbone.
- Test macro-F1: 0.0273.

The stronger focus run is the checkpoint that should be used for demos and follow-up experiments:

- Checkpoint: `artifacts/checkpoints/focus/best_classifier.pt`
- Config: 10 epochs, 224px crops, ImageNet-pretrained ResNet-18, balanced focus manifest.
- Best validation macro-F1: 0.5773.
- Bounded held-out test sample: 12,000 crops.
- Bounded test macro-F1: 0.5199.
- Bounded test per-class F1: no_damage 0.7434, minor_damage 0.2166, major_damage 0.3408, destroyed 0.7789.

Interpretation:

- The model has credible signal for `no_damage` and `destroyed`.
- The main weakness is confusion among `minor_damage`, `major_damage`, and neighbouring no-damage examples.
- This is a model/data boundary problem, not a dashboard problem.

## Industry-style improvement ladder

1. Promote only evaluated checkpoints.
   - Do not present smoke-test outputs as model performance.
   - Every promoted checkpoint needs manifest name, split, crop size, class strategy, macro-F1, per-class F1, and confusion matrix.

2. Improve the training data before changing architecture.
   - Audit 50-100 errors from the confusion matrix, especially `minor_damage` predicted as `no_damage` or `major_damage`.
   - Check crop alignment, label quality, tiny buildings, heavy cloud/smoke, and cases where the damage is outside the crop padding.
   - Increase crop padding experiments: 12px baseline, then 24px and 32px. Damage context often matters more than the building footprint alone.

3. Run controlled experiments.
   - Baseline: current 6-channel ResNet-18, 224px, loss weights.
   - Experiment A: `class_weight_strategy=sampler`.
   - Experiment B: `class_weight_strategy=both`.
   - Experiment C: stronger regularisation, dropout 0.5 and 15 epochs with early stopping.
   - Experiment D: larger context crops from padding 24 or 32.
   - Compare by held-out macro-F1 and per-class F1, not accuracy.

4. Add task-level reporting.
   - Keep 4-class metrics for technical honesty.
   - Also report a 3-class rollup: `no_damage`, `damaged` (`minor_damage` + `major_damage`), `destroyed`.
   - Optionally report a 2-class triage rollup: `no/low` vs `significant` (`major_damage` + `destroyed`).
   - This does not hide the 4-class weakness; it explains what the prototype can support reliably.

5. Consider architecture only after data experiments.
   - A Siamese/two-tower ResNet can improve pre/post comparison, but it adds complexity.
   - A larger backbone can overfit quickly on event-specific data.
   - Do not add segmentation for performance unless the MVP is explicitly expanded.

## Recommended next commands

Full held-out evaluation for the promoted checkpoint:

```powershell
python -m src.models.evaluate --checkpoint artifacts/checkpoints/focus/best_classifier.pt --manifest artifacts/manifests/crop_manifest_focus.csv --split test --batch-size 64 --num-workers 2 --save-figure
```

Regenerate dashboard cache from the promoted checkpoint:

```powershell
python -m src.inference.generate_predictions --checkpoint artifacts/checkpoints/focus/best_classifier.pt --manifest artifacts/manifests/crop_manifest_focus.csv --split test --batch-size 64 --num-workers 2
```

Run a bounded fast check when iterating:

```powershell
python -m src.models.evaluate --checkpoint artifacts/checkpoints/focus/best_classifier.pt --manifest artifacts/manifests/crop_manifest_focus.csv --split test --batch-size 64 --num-workers 2 --max-samples 12000 --save-figure
```
