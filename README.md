# DisasterSight

**AI-Assisted Satellite Damage Triage Dashboard for Rapid Post-Disaster Assessment**

DisasterSight is a Monash DeepNeuron AI/ML project that uses pre-disaster and post-disaster satellite imagery to support rapid visual assessment of building damage after natural disasters.

The project combines computer vision, geospatial preprocessing, and an interactive dashboard to help users inspect damaged areas, view model predictions, and prioritise zones for human review.

> DisasterSight is an academic decision-support prototype. It is not intended for autonomous emergency response, operational dispatch, or real-world disaster decision-making without expert validation.

---

## Project Overview

After a natural disaster, response teams often need to quickly understand which areas are most affected. Manual inspection of large satellite imagery datasets can be slow and difficult to scale.

DisasterSight aims to address this by building a prototype that can:

- Compare pre-disaster and post-disaster satellite imagery
- Detect or localise buildings
- Estimate building damage severity
- Visualise damage predictions on an interactive dashboard
- Summarise damage by severity level
- Rank zones using a simple response-priority score
- Flag uncertain predictions for human review

---

## Key Features

### MVP Features

- Pre/post satellite image pair selection
- Building damage prediction pipeline
- Damage severity overlay visualisation
- Summary statistics for affected buildings
- Simple zone-level priority score
- Confidence or uncertainty flag for human review
- Streamlit dashboard for industry-night demonstration

### Stretch Features

- Flooded-road or access-layer visualisation
- Optional FastAPI inference endpoint
- Exportable summary report or screenshot
- Human override notes for review

---

## Tech Stack

| Area | Tools |
|---|---|
| Programming language | Python |
| Machine learning | PyTorch |
| Image processing | OpenCV, Pillow, NumPy |
| Geospatial processing | Rasterio, GeoPandas |
| Data handling | Pandas |
| Evaluation | scikit-learn |
| Dashboard | Streamlit |
| Optional API | FastAPI |
| Version control | Git, GitHub |
| Compute | Local machines, Google Colab, Kaggle Notebooks |

---

## Proposed System Pipeline

```text
Pre-disaster image
        |
        v
Post-disaster image
        |
        v
Image pairing and preprocessing
        |
        v
Building localisation / segmentation
        |
        v
Damage severity classification
        |
        v
Zone-level aggregation and priority scoring
        |
        v
Interactive dashboard visualisation
