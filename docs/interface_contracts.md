# Interface Contracts

## Purpose

Define the minimal contracts between preprocessing, modeling, cached inference, and the Streamlit dashboard so each module can be implemented independently.

## 1. Scene Record Contract

One scene record represents a paired pre/post disaster image set.

Required fields:

| Field | Type | Description |
|---|---|---|
| `scene_id` | `str` | Unique xBD scene identifier |
| `disaster_name` | `str` | Event name or folder label |
| `disaster_type` | `str` | Disaster category |
| `pre_image_path` | `str` | Relative path to pre-disaster image |
| `post_image_path` | `str` | Relative path to post-disaster image |
| `pre_json_path` | `str` | Relative path to pre-disaster xBD metadata |
| `post_json_path` | `str` | Relative path to post-disaster xBD labels/metadata |
| `label_json_path` | `str` | Relative path to xBD labels/metadata |
| `split` | `str` | `train`, `val`, or `test` |

Manifest paths should be repository-relative when the files live under the project root.

## 2. Building Record Contract

One building record represents a single xBD polygon and label.

Damage labels should use canonical config names with underscores:
`no_damage`, `minor_damage`, `major_damage`, and `destroyed`.

Required fields:

| Field | Type | Description |
|---|---|---|
| `building_id` | `str` | Stable per-scene building identifier |
| `scene_id` | `str` | Parent scene id |
| `disaster_name` | `str` | Parent disaster/event name |
| `disaster_type` | `str` | Parent disaster category |
| `split` | `str` | Dataset split inherited from the scene manifest |
| `geometry_source` | `str` | Source used to derive geometry, such as `wkt`, `geometry`, or `bbox` |
| `polygon_xy` | `str` | JSON-serialized pixel-coordinate polygon points, or an empty list for bbox-only records |
| `bbox_x1` / `bbox_y1` / `bbox_x2` / `bbox_y2` | `int` | Crop bounding box in pixel coordinates |
| `damage_label` | `str` | One of configured damage classes |
| `crop_width` / `crop_height` | `int` | Padded crop dimensions before resizing |
| `pre_crop_path` | `str` | Relative path to saved pre-disaster crop |
| `post_crop_path` | `str` | Relative path to saved post-disaster crop |
| `pre_masked_crop_path` | `str` | Optional relative path to masked pre-disaster crop |
| `post_masked_crop_path` | `str` | Optional relative path to masked post-disaster crop |
| `area_pixels` | `int` | Polygon or mask area in pixels |

Validation expectations:
- Required crop paths must exist locally before training starts.
- `damage_label` must be one of the configured damage classes.
- `split` must be populated.
- Bounding boxes and crop dimensions must be positive.

## 3. Model Input Contract

The baseline classifier should consume:

| Input | Type | Notes |
|---|---|---|
| `pre_image` | tensor | RGB crop resized to configured image size |
| `post_image` | tensor | RGB crop resized to configured image size |
| `label` | integer | Encoded damage class |
| `metadata` | dict | Optional scene/building identifiers for debugging |

Baseline assumption:
- The classifier is paired-image only.
- No segmentation masks are required for the MVP training loop.

## 4. Prediction Contract

Cached building-level predictions must contain:

| Field | Type | Description |
|---|---|---|
| `scene_id` | `str` | Scene identifier |
| `building_id` | `str` | Building identifier |
| `predicted_label` | `str` | Predicted damage class |
| `confidence` | `float` | Top-class probability or calibrated score |
| `needs_review` | `bool` | True if below review threshold |
| `class_probabilities` | `dict[str, float]` | Per-class probabilities |

Current cache artifact:

```text
artifacts/predictions/building_predictions_{split}.csv
```

The CSV stores `class_probabilities` as compact JSON and carries overlay fields
from the crop manifest: `polygon_xy`, `bbox_x1`, `bbox_y1`, `bbox_x2`,
`bbox_y2`, `pre_crop_path`, and `post_crop_path`.

## 5. Zone Summary Contract

The dashboard summary layer should be able to compute or load:

| Field | Type | Description |
|---|---|---|
| `scene_id` | `str` | Scene identifier |
| `total_buildings` | `int` | Total assessed buildings |
| `class_counts` | `dict[str, int]` | Count by damage class |
| `destroyed_share` | `float` | Destroyed count / total |
| `major_damage_share` | `float` | Major-damage count / total |
| `damage_density` | `float` | Damaged buildings / visible building count |
| `priority_score` | `float` | Demo score from documented formula |
| `review_flag_count` | `int` | Number of buildings flagged for review |

Priority score formula for the MVP:

```text
100 * (0.50 * destroyed_share + 0.30 * major_damage_share + 0.20 * damage_density)
```

Current cache artifact:

```text
artifacts/predictions/scene_summaries_{split}.csv
```

## 6. Dashboard Contract

The Streamlit app loads data through ``src/dashboard/artifact_resolver.py``,
which resolves artifacts from configured paths with fixture fallback.

Data sources (in resolution order):

| Artifact | Primary Path | Inference fallback | Offline fallback |
|---|---|---|---|
| Scene manifest | `data/processed/scenes.json` | `artifacts/manifests/scene_manifest.csv` | `src/dashboard/fixtures/demo_scenes.json` |
| Zone summaries | `artifacts/zone_summaries.json` | `artifacts/predictions/scene_summaries_{split}.csv` | `src/dashboard/fixtures/demo_zone_summaries.json` |
| Predictions | `artifacts/predictions/{scene_id}.json` | `artifacts/predictions/building_predictions_{split}.csv` | `src/dashboard/fixtures/demo_predictions.jsonl` |
| Metrics | `artifacts/metrics.json` | `artifacts/figures/eval_results_{split}.json` | `src/dashboard/fixtures/demo_metrics.json` |
| Confusion matrix | `artifacts/figures/confusion_matrix.png` | Generated heatmap |
| Failure cases | `artifacts/figures/failures/*.png` | Placeholder cards |

Architecture layers:

- ``artifact_resolver.py`` — pure file resolution and I/O (no Streamlit dependency, fully testable)
- ``data_loaders.py`` — thin Streamlit-cached facade with fixture-fallback warnings
- ``components/`` — reusable UI components with ``render`` entry-points
- ``pages/`` — multi-page scripts loaded by ``st.navigation``

The dashboard should not assume:

- Live model inference
- GPU availability
- Any segmentation model outputs

## 7. Responsible-AI Contract

Every user-facing view should preserve these messages:

- This is an academic prototype.
- Outputs are decision support only.
- Low-confidence results must be marked for human review.
- The system is not suitable for autonomous dispatch or real emergency operations.
