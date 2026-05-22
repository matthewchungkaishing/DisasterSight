# AGENTS.md — src/data/

## Module purpose

xBD/xView2 data pipeline: scan raw imagery, parse annotations, build manifests, extract paired building crops, and validate outputs.

## Pipeline order

1. `build_scene_manifest.py` — scan xBD root, pair pre/post files, apply event-aware train/val/test splits.
2. `build_crop_manifest.py` — extract paired pre/post building crops from scenes using polygons.
3. `validate_crop_manifest.py` — validate schema, paths, labels, bounding boxes, and splits.
4. `build_crop_qa_preview.py` — generate a contact-sheet preview for visual QA.

## Key conventions

- Scene records must follow the contract in `docs/interface_contracts.md` (fields: `scene_id`, `disaster_name`, `disaster_type`, `pre_image_path`, `post_image_path`, `split`, etc.).
- Building records must include `building_id`, `scene_id`, `damage_label`, `polygon_xy`, `bbox_*`, `pre_crop_path`, `post_crop_path`, and `split`.
- Train/val/test splitting is **event-aware**: all scenes from the same disaster event go to the same split to prevent data leakage.
- Damage labels use canonical underscore names: `no_damage`, `minor_damage`, `major_damage`, `destroyed`. Raw xBD labels are normalised via `xbd.normalise_label()`.
- Paths in manifests should be repository-relative, not absolute.

## What not to do

- Do not add non-xBD datasets without explicit request.
- Do not hardcode absolute paths — use `config.yaml` via `src.common.paths`.
- Do not bypass `normalise_label()` when reading damage labels.
- Do not mix scenes across splits within the same disaster event.

## Testing

- Tests live in `tests/test_xbd.py`.
- Use `tempfile.TemporaryDirectory` for file-system fixtures.
- Test parsing, label normalisation, event-aware splitting, crop extraction, and manifest validation.
