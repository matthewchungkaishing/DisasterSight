# AGENTS.md — src/models/

## Module purpose

Baseline paired-image damage classifier for xBD building crops. This package owns model architecture, dataset loading, training, and evaluation.

## Architecture

- **PairedCropClassifier**: ResNet-18 backbone modified for 6-channel input (pre + post concatenated along channel axis). Pretrained ImageNet weights are duplicated across both channel halves and scaled by 0.5.
- **CropDataset**: PyTorch Dataset that reads from a validated crop manifest CSV. Yields `(6, H, W)` tensors with synchronised geometric augmentation and independent colour jitter.

## Key conventions

- All hyperparameters come from `config.yaml` under `training:`. CLI flags override config values.
- Class imbalance is handled via `class_weight_strategy` in config: `loss_weight`, `sampler`, `both`, or `none`.
- Checkpoints save model state, optimizer state, scheduler state, val macro F1, config snapshot, and class names.
- The best checkpoint is selected by highest validation macro F1.
- Evaluation must report macro F1, per-class F1, and confusion matrix.
- Labels must use canonical names from `src.common.constants.DAMAGE_CLASSES`: `no_damage`, `minor_damage`, `major_damage`, `destroyed`.

## What not to do

- Do not add segmentation models, attention mechanisms, or multi-scale architectures unless explicitly requested.
- Do not hardcode absolute paths — use `config.yaml` and `src.common.paths`.
- Do not import Streamlit or dashboard code from this package.
- Do not add new damage classes without updating `constants.py`, `config.yaml`, and `interface_contracts.md`.

## Testing

- Tests live in `tests/test_models.py`.
- Use dummy manifests with `tempfile.TemporaryDirectory` for isolation.
- Test the forward pass shape, checkpoint round-trip, class weight computation, and dataset loading.
