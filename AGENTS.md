# AGENTS.md

## Project: DisasterSight

DisasterSight is a Monash DeepNeuron AI/ML project. The goal is to build a Streamlit dashboard for AI-assisted satellite damage triage using xBD/xView2 pre/post-disaster imagery.

## Core MVP

The MVP must:
1. Use xBD/xView2 as the primary dataset.
2. Use xBD building polygons for building localisation first.
3. Extract paired pre-disaster and post-disaster building crops.
4. Train a simple damage classifier.
5. Generate cached predictions.
6. Display results in a Streamlit dashboard.
7. Show overlays, severity counts, priority score, confidence, and human-review flags.
8. Include evaluation using macro F1 and confusion matrix.

## Strict scope control

Do not implement these unless explicitly requested:
- U-Net segmentation
- SpaceNet 8 roads/flooding
- FastAPI backend
- React frontend
- live satellite ingestion
- cloud deployment
- route optimisation
- production emergency-response claims

## Coding style

- Use Python.
- Keep files modular.
- Avoid huge scripts.
- Add clear comments.
- Do not hardcode absolute local machine paths.
- Use config.yaml for paths.
- Functions should be testable.
- Prefer simple, reliable code over complex abstractions.

## Data policy

- Do not commit raw xBD images.
- Do not commit large processed datasets.
- Do not commit model checkpoints unless they are tiny demo files.
- Use data/README.md to explain where data should go.

## Dashboard principles

The Streamlit dashboard should be understandable in a 2-minute industry-night walkthrough:
1. Select disaster scene.
2. View pre/post image.
3. Toggle damage overlay.
4. See severity counts.
5. See priority score.
6. See review-required flags.
7. See model evaluation and limitations.

## Responsible AI framing

Always frame the system as:
- academic prototype
- decision-support tool
- human-in-the-loop
- not a real emergency dispatch system