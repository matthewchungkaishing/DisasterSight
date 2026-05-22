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
| `label_json_path` | `str` | Relative path to xBD labels/metadata |
| `split` | `str` | `train`, `val`, or `test` |

## 2. Building Record Contract

One building record represents a single xBD polygon and label.

Damage labels should use canonical config names with underscores:
`no_damage`, `minor_damage`, `major_damage`, and `destroyed`.

Required fields:

| Field | Type | Description |
|---|---|---|
| `building_id` | `str` | Stable per-scene building identifier |
| `scene_id` | `str` | Parent scene id |
| `polygon_wkt` | `str` | Building polygon in WKT or equivalent serialized form |
| `bbox_xyxy` | `list[int]` | Crop bounding box in pixel coordinates |
| `damage_label` | `str` | One of configured damage classes |
| `pre_crop_path` | `str` | Relative path to saved pre-disaster crop |
| `post_crop_path` | `str` | Relative path to saved post-disaster crop |
| `area_pixels` | `int` | Polygon or mask area in pixels |

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

## 6. Dashboard Contract

The Streamlit app should assume it can load:

- A list of available scenes
- Scene-level image paths
- Building polygons or bounding boxes for overlays
- Cached building predictions
- Aggregated scene summary metrics
- Evaluation artifacts such as confusion matrix figures

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
