# Data Layout

This repository expects xBD/xView2 data to be available locally, but raw imagery and generated datasets must not be committed.

## Expected Structure

```text
data/
  raw/
    xbd/
      train/
      test/
      tier3/
  interim/
  processed/
  cache/
```

The exact nested folder names may follow the original xBD archive layout. Project code should discover files from `paths.xbd_root` in `config.yaml` instead of relying on absolute local paths.

## What Can Be Committed

- This README
- Small hand-written examples for tests, if needed
- Documentation describing generated outputs

## What Must Stay Local

- Raw xBD images and labels
- Extracted building crops
- Processed manifests derived from the full dataset
- Cached predictions
- Model checkpoints, unless a tiny demo artifact is explicitly approved

## Generated Outputs

Current and future commands write generated data under configured local directories:

- `data/processed/`: exploratory scene summaries and label summaries
- `data/interim/`: intermediate crop metadata or QA tables
- `data/cache/`: local dashboard caches
- `artifacts/manifests/`: train/validation/test scene and crop manifests
- `artifacts/predictions/`: cached model predictions
- `artifacts/figures/`: QA previews and evaluation figures

All of these paths are ignored by git by default.

## Responsible Use

DisasterSight uses public historical benchmark data for an academic prototype. Do not add live satellite feeds, sensitive operational data, or emergency-response claims without explicit project approval.
