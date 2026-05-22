# Foundation Guardrails

Use this checklist before adding new functionality so the project stays aligned with the DisasterSight MVP.

## Scope

- Keep xBD/xView2 as the primary dataset.
- Use xBD building polygons for localisation before considering any learned segmentation.
- Keep the dashboard as Streamlit unless a new requirement explicitly changes the frontend scope.
- Treat all outputs as academic decision support for human review.
- Do not add operational emergency-response, dispatch, routing, cloud deployment, or live-ingestion claims.

## Data Boundaries

- Read all local paths from `config.yaml`.
- Keep generated data under `data/interim`, `data/processed`, `data/cache`, or `artifacts`.
- Keep raw xBD imagery, generated crops, cached predictions, and model checkpoints out of git.
- Store manifest paths relative to the repository when files live under the project root.

## Engineering Bar

- Prefer small modules with testable functions over large scripts.
- Add or update interface contracts when a preprocessing, modeling, inference, or dashboard output changes.
- Add focused tests for parser behavior, manifest schema, crop metadata, labels, and metric outputs.
- Run these before moving to the next phase:

```powershell
python -m ruff check .
python -m unittest discover -s tests
python -m compileall -q src tests
```

## Next-Phase Gate

Before starting classifier work, confirm:

- The scene manifest is generated from complete pre/post image and JSON pairs only.
- Small-subset manifests are deterministic and keep disaster events whole.
- The crop manifest has stable `scene_id`, `building_id`, `damage_label`, crop paths, polygon, bbox, and split fields.
- The crop manifest passes `python -m src.data.validate_crop_manifest`.
- A crop QA preview has been generated with `python -m src.data.build_crop_qa_preview`.
- The label set remains `no_damage`, `minor_damage`, `major_damage`, and `destroyed`.
- Any evaluation report includes macro F1 and a confusion matrix.
