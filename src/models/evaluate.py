"""Phase 3 evaluation script: macro F1, per-class F1, and confusion matrix.

Usage:
    python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt
    python -m src.models.evaluate --checkpoint ... --split test
    python -m src.models.evaluate --checkpoint ... --split val --save-figure

Outputs:
  - Console: macro F1, per-class F1, confusion matrix
  - JSON:    artifacts/figures/eval_results_{split}.json
  - PNG:     artifacts/figures/confusion_matrix_{split}.png  (with --save-figure)
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch.utils.data import DataLoader

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import ensure_project_dirs, load_config
from src.models.classifier import PairedCropClassifier
from src.models.crop_dataset import NUM_CLASSES, CropDataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the trained damage classifier.")
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to the .pt checkpoint produced by train.py.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Crop manifest CSV (default: artifacts/manifests/crop_manifest.csv).",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["train", "val", "test"],
        help="Which manifest split to evaluate (default: test).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch size for inference (default from config.yaml).",
    )
    parser.add_argument(
        "--save-figure",
        action="store_true",
        help="Save a confusion-matrix PNG to artifacts/figures/.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: list[str],
    title: str = "Confusion Matrix",
) -> plt.Figure:
    """Return a matplotlib Figure containing a labelled confusion matrix heatmap."""
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    fig.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        title=title,
        ylabel="True label",
        xlabel="Predicted label",
    )
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                str(cm[i, j]),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=10,
            )

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate(
    checkpoint_path: Path,
    manifest_path: Path,
    split: str,
    *,
    batch_size: int = 16,
    num_workers: int = 2,
    save_figure: bool = False,
    figures_dir: Path | None = None,
) -> dict:
    """Run inference on ``split``, compute metrics, and return a result dict."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Device: %s", device)
    log.info("Loading checkpoint: %s", checkpoint_path)

    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )
    saved_config = checkpoint.get("config", {})
    image_size: int = saved_config.get("image_size", 224)
    dropout: float = saved_config.get("dropout", 0.3)

    model = PairedCropClassifier(pretrained=False, dropout=dropout).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dataset = CropDataset(
        manifest_path,
        split=split,
        image_size=image_size,
        augment=False,
    )
    if len(dataset) == 0:
        raise ValueError(f"Split '{split}' is empty in manifest {manifest_path}.")
    log.info("Evaluating %d samples from '%s' split.", len(dataset), split)

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    all_preds: list[int] = []
    all_labels: list[int] = []
    all_confidences: list[float] = []

    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=-1)
            max_probs, preds = probs.max(dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_confidences.extend(max_probs.cpu().tolist())

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    macro_f1 = float(
        f1_score(
            all_labels,
            all_preds,
            average="macro",
            zero_division=0,
            labels=list(range(NUM_CLASSES)),
        )
    )
    per_class_f1 = f1_score(
        all_labels,
        all_preds,
        average=None,
        zero_division=0,
        labels=list(range(NUM_CLASSES)),
    )
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(NUM_CLASSES)))
    report = classification_report(
        all_labels,
        all_preds,
        target_names=list(DAMAGE_CLASSES),
        labels=list(range(NUM_CLASSES)),
        zero_division=0,
    )

    mean_confidence = sum(all_confidences) / max(len(all_confidences), 1)
    low_confidence_count = sum(1 for c in all_confidences if c < 0.5)

    log.info("\n%s split evaluation (%d samples)", split.upper(), len(all_labels))
    log.info("Macro F1: %.4f", macro_f1)
    log.info(
        "Per-class F1:\n%s",
        "\n".join(f"  {DAMAGE_CLASSES[i]:>15}: {per_class_f1[i]:.4f}" for i in range(NUM_CLASSES)),
    )
    log.info("Mean confidence: %.4f", mean_confidence)
    log.info(
        "Low-confidence predictions (<0.5): %d / %d (%.1f%%)",
        low_confidence_count,
        len(all_confidences),
        100 * low_confidence_count / max(len(all_confidences), 1),
    )
    log.info("Classification report:\n%s", report)
    log.info("Confusion matrix (rows=true, cols=predicted):")
    log.info("  Classes: %s", " | ".join(DAMAGE_CLASSES))
    for i, cm_row in enumerate(cm):
        log.info("  %s: %s", DAMAGE_CLASSES[i], cm_row.tolist())

    result = {
        "split": split,
        "num_samples": len(all_labels),
        "macro_f1": macro_f1,
        "mean_confidence": round(mean_confidence, 4),
        "low_confidence_count": low_confidence_count,
        "per_class_f1": {
            DAMAGE_CLASSES[i]: round(float(per_class_f1[i]), 4) for i in range(NUM_CLASSES)
        },
        "confusion_matrix": {
            "classes": list(DAMAGE_CLASSES),
            "matrix": cm.tolist(),
        },
        "checkpoint": str(checkpoint_path),
        "training_config": saved_config,
    }

    # ------------------------------------------------------------------
    # Optional figure
    # ------------------------------------------------------------------
    if save_figure and figures_dir is not None:
        figures_dir.mkdir(parents=True, exist_ok=True)
        fig = plot_confusion_matrix(
            cm,
            class_names=list(DAMAGE_CLASSES),
            title=f"Confusion Matrix \u2013 {split} split (macro F1={macro_f1:.3f})",
        )
        fig_path = figures_dir / f"confusion_matrix_{split}.png"
        fig.savefig(fig_path, dpi=150)
        plt.close(fig)
        log.info("Confusion matrix figure saved to %s", fig_path)
        result["figure_path"] = str(fig_path)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = ensure_project_dirs(config)
    training_cfg = config.get("training", {})

    manifest_path = (
        Path(args.manifest) if args.manifest else path_map["manifests_dir"] / "crop_manifest.csv"
    )
    batch_size = args.batch_size or int(training_cfg.get("batch_size", 16))
    num_workers = int(training_cfg.get("num_workers", 2))
    checkpoint_path = Path(args.checkpoint)

    if not checkpoint_path.exists():
        log.error("Checkpoint not found: %s", checkpoint_path)
        return 1
    if not manifest_path.exists():
        log.error("Manifest not found: %s", manifest_path)
        return 1

    result = evaluate(
        checkpoint_path=checkpoint_path,
        manifest_path=manifest_path,
        split=args.split,
        batch_size=batch_size,
        num_workers=num_workers,
        save_figure=args.save_figure,
        figures_dir=path_map["figures_dir"],
    )

    results_path = path_map["figures_dir"] / f"eval_results_{args.split}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    log.info("Evaluation results saved to %s", results_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
