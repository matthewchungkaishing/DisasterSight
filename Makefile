.PHONY: lint lint-fix typecheck test compile-check quality train evaluate predictions validate-crops qa-preview pipeline full-pipeline dashboard help

PYTHON ?= python

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Quality gates (match foundation_guardrails.md)
# ---------------------------------------------------------------------------

lint: ## Run ruff linter
	$(PYTHON) -m ruff check .

lint-fix: ## Run ruff with auto-fix
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

typecheck: ## Run mypy type checker
	$(PYTHON) -m mypy src/ tests/

test: ## Run unit tests
	$(PYTHON) -m unittest discover -s tests

compile-check: ## Verify all Python files compile
	$(PYTHON) -m compileall -q src tests

quality: lint typecheck test compile-check ## Run all quality gates

# ---------------------------------------------------------------------------
# Data pipeline
# ---------------------------------------------------------------------------

validate-crops: ## Validate the crop manifest
	$(PYTHON) -m src.data.validate_crop_manifest

qa-preview: ## Generate crop QA contact sheet
	$(PYTHON) -m src.data.build_crop_qa_preview

# ---------------------------------------------------------------------------
# Model training and evaluation
# ---------------------------------------------------------------------------

train: ## Train the baseline damage classifier
	$(PYTHON) -m src.models.train

evaluate: ## Evaluate the trained classifier (requires CHECKPOINT arg)
	$(PYTHON) -m src.models.evaluate --checkpoint $(CHECKPOINT) --save-figure

predictions: ## Cache dashboard predictions (requires CHECKPOINT arg)
	$(PYTHON) -m src.inference.generate_predictions --checkpoint $(CHECKPOINT)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

dashboard: ## Launch the Streamlit dashboard
	streamlit run src/dashboard/app.py

# ---------------------------------------------------------------------------
# Full pipeline (data → train → evaluate → cache → dashboard)
# ---------------------------------------------------------------------------

pipeline: ## Run data pipeline: manifest -> crops -> validate -> QA
	$(PYTHON) -m src.data.build_scene_manifest --all-scenes
	$(PYTHON) -m src.data.build_crop_manifest --clean --max-per-class 10000
	$(PYTHON) -m src.data.validate_crop_manifest
	$(PYTHON) -m src.data.build_crop_qa_preview
	@echo "Data pipeline complete. Run 'make train' then 'make evaluate CHECKPOINT=...' and 'make predictions CHECKPOINT=...'."

full-pipeline: ## Run end-to-end: data -> train -> evaluate -> predictions
	$(MAKE) pipeline
	$(MAKE) train
	$(MAKE) evaluate CHECKPOINT=artifacts/checkpoints/best_classifier.pt
	$(MAKE) predictions CHECKPOINT=artifacts/checkpoints/best_classifier.pt
	@echo "Full pipeline complete. Run 'make dashboard' to view real artifacts."
