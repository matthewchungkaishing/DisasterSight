"""Phase 3 evaluation script: macro F1, per-class F1, and confusion matrix.

Usage:
    python -m src.models.evaluate --checkpoint artifacts/checkpoints/best_classifier.pt
    python -m src.models.evaluate --checkpoint ... --split test
    python -m src.models.evaluate --checkpoint ... --split val --save-figure

Outputs:
  - Console: macro F1, per-class F1, confusion matrix
  - JSON:    artifacts/figures/eval_results_{split}.json
  - JSON:    artifacts/metrics.json (dashboard format, always written)
  - PNG:     artifacts/figures/confusion_matrix_{split}.png  (with --save-figure)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from torch.utils.data import DataLoader

from src.common.classification_metrics import (
    classification_report_text,
    confusion_matrix_counts,
    macro_scores,
    metrics_summary,
    per_class_precision_recall_f1,
    remap_confusion_matrix,
)
from src.common.constants import DAMAGE_CLASSES
from src.common.metrics_format import format_dashboard_metrics
from src.common.paths import ensure_project_dirs, load_config
from src.models.classifier import PairedCropClassifier
from src.models.crop_dataset import (
    NUM_CLASSES,
    CropDataset,
    load_crop_records,
    stratified_sample_records,
)

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
        "--num-workers",
        type=int,
        default=None,
        help="Override DataLoader workers (default from config.yaml).",
    )
    parser.add_argument(
        "--save-figure",
        action="store_true",
        help="Save a confusion-matrix PNG to artifacts/figures/.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Class-aware cap for evaluation rows. Intended for CPU smoke runs on real xBD crops.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def plot_confusion_matrix(
    cm: list[list[int]],
    class_names: list[str],
    title: str = "Confusion Matrix",
) -> Image.Image:
    """Return a labelled confusion-matrix heatmap image without matplotlib."""
    cell = 76
    left = 150
    top = 84
    right = 24
    bottom = 34
    size = len(class_names)
    width = left + size * cell + right
    height = top + size * cell + bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    draw.text((left, 18), title, fill=(18, 27, 38))
    draw.text((left + size * cell // 2 - 40, height - 24), "Predicted label", fill=(52, 64, 84))
    draw.text((12, top - 34), "True label", fill=(52, 64, 84))

    max_value = max((value for row in cm for value in row), default=0)
    for index, label in enumerate(class_names):
        x = left + index * cell
        y = top + index * cell
        draw.text((x + 6, top - 24), label.replace("_", "\n"), fill=(52, 64, 84))
        draw.text((12, y + cell // 2 - 8), label, fill=(52, 64, 84))

    for row_idx, row in enumerate(cm):
        for col_idx, value in enumerate(row):
            intensity = int(235 - 170 * (value / max_value)) if max_value else 235
            fill = (intensity, intensity + 8, 255)
            x1 = left + col_idx * cell
            y1 = top + row_idx * cell
            x2 = x1 + cell
            y2 = y1 + cell
            draw.rectangle((x1, y1, x2, y2), fill=fill, outline=(207, 216, 226))
            text_color = "white" if value > max_value / 2 else (18, 27, 38)
            draw.text((x1 + cell // 2 - 8, y1 + cell // 2 - 8), str(value), fill=text_color)

    return image


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
    artifacts_dir: Path | None = None,
    figures_dir: Path | None = None,
    max_samples: int | None = None,
    seed: int = 42,
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

    records = stratified_sample_records(
        load_crop_records(manifest_path, split),
        max_samples,
        seed=seed,
    )
    dataset = CropDataset(
        None,
        split=split,
        image_size=image_size,
        augment=False,
        records=records,
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
    all_record_indices: list[int] = []

    with torch.no_grad():
        seen = 0
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=-1)
            max_probs, preds = probs.max(dim=-1)
            batch_size_actual = labels.size(0)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_confidences.extend(max_probs.cpu().tolist())
            all_record_indices.extend(range(seen, seen + batch_size_actual))
            seen += batch_size_actual

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    cm_counts = confusion_matrix_counts(all_labels, all_preds, num_classes=NUM_CLASSES)
    precision_macro, recall_macro, macro_f1 = macro_scores(cm_counts)
    _precision, _recall, per_class_f1 = per_class_precision_recall_f1(cm_counts)
    report = classification_report_text(cm_counts, list(DAMAGE_CLASSES))

    mean_confidence = sum(all_confidences) / max(len(all_confidences), 1)
    low_confidence_count = sum(1 for c in all_confidences if c < 0.5)

    log.info("\n%s split evaluation (%d samples)", split.upper(), len(all_labels))
    log.info(
        "Macro F1: %.4f | Precision: %.4f | Recall: %.4f",
        macro_f1,
        precision_macro,
        recall_macro,
    )
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
    for i, cm_row in enumerate(cm_counts):
        log.info("  %s: %s", DAMAGE_CLASSES[i], cm_row)

    result = {
        "split": split,
        "num_samples": len(all_labels),
        "macro_f1": round(macro_f1, 4),
        "precision_macro": round(precision_macro, 4),
        "recall_macro": round(recall_macro, 4),
        "mean_confidence": round(mean_confidence, 4),
        "low_confidence_count": low_confidence_count,
        "per_class_f1": {
            DAMAGE_CLASSES[i]: round(float(per_class_f1[i]), 4) for i in range(NUM_CLASSES)
        },
        "confusion_matrix": {
            "classes": list(DAMAGE_CLASSES),
            "matrix": cm_counts,
        },
        "checkpoint": str(checkpoint_path),
        "training_config": saved_config,
        "rollup_metrics": _build_rollup_metrics(all_labels, all_preds),
    }

    # ------------------------------------------------------------------
    # Optional figure + failure cases + dashboard metrics export
    # ------------------------------------------------------------------
    if save_figure and figures_dir is not None:
        figures_dir.mkdir(parents=True, exist_ok=True)
        image = plot_confusion_matrix(
            cm_counts,
            class_names=list(DAMAGE_CLASSES),
            title=f"Confusion Matrix - {split} split (macro F1={macro_f1:.3f})",
        )
        fig_path = figures_dir / f"confusion_matrix_{split}.png"
        image.save(fig_path)
        log.info("Confusion matrix figure saved to %s", fig_path)
        result["figure_path"] = str(fig_path)

    if figures_dir is not None:
        failures_path = figures_dir / f"failure_cases_{split}.csv"
        _write_failure_cases(
            failures_path,
            records=records,
            record_indices=all_record_indices,
            labels=all_labels,
            preds=all_preds,
            confidences=all_confidences,
            limit=100,
        )
        result["failure_cases_path"] = str(failures_path)
        log.info("Failure-case CSV saved to %s", failures_path)

    return result


def _build_rollup_metrics(labels: list[int], preds: list[int]) -> dict[str, dict[str, object]]:
    """Return coarser triage metrics without changing the primary 4-class task."""
    three_class_names = ["no_damage", "damaged", "destroyed"]
    three_class_cm = remap_confusion_matrix(
        labels,
        preds,
        class_mapping={
            0: 0,  # no_damage
            1: 1,  # minor_damage -> damaged
            2: 1,  # major_damage -> damaged
            3: 2,  # destroyed
        },
        num_classes=len(three_class_names),
    )

    binary_names = ["no_low_damage", "significant_damage"]
    binary_cm = remap_confusion_matrix(
        labels,
        preds,
        class_mapping={
            0: 0,  # no_damage
            1: 0,  # minor_damage
            2: 1,  # major_damage
            3: 1,  # destroyed
        },
        num_classes=len(binary_names),
    )

    return {
        "three_class": metrics_summary(three_class_cm, three_class_names),
        "binary_triage": metrics_summary(binary_cm, binary_names),
    }


def _write_failure_cases(
    path: Path,
    *,
    records: list[dict[str, str]],
    record_indices: list[int],
    labels: list[int],
    preds: list[int],
    confidences: list[float],
    limit: int,
) -> None:
    """Write the highest-confidence mistakes for human error review."""
    fieldnames = [
        "scene_id",
        "building_id",
        "true_label",
        "predicted_label",
        "confidence",
        "disaster_name",
        "disaster_type",
        "pre_crop_path",
        "post_crop_path",
    ]
    mistakes: list[dict[str, str | float]] = []
    for record_idx, true_idx, pred_idx, confidence in zip(
        record_indices,
        labels,
        preds,
        confidences,
        strict=True,
    ):
        if true_idx == pred_idx:
            continue
        record = records[record_idx]
        mistakes.append(
            {
                "scene_id": record.get("scene_id", ""),
                "building_id": record.get("building_id", ""),
                "true_label": DAMAGE_CLASSES[true_idx],
                "predicted_label": DAMAGE_CLASSES[pred_idx],
                "confidence": round(float(confidence), 6),
                "disaster_name": record.get("disaster_name", ""),
                "disaster_type": record.get("disaster_type", ""),
                "pre_crop_path": record.get("pre_crop_path", ""),
                "post_crop_path": record.get("post_crop_path", ""),
            }
        )

    mistakes.sort(key=lambda row: float(row["confidence"]), reverse=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mistakes[:limit])


def _write_dashboard_metrics(
    eval_result: dict,
    *,
    artifacts_dir: Path,
    figures_dir: Path,
) -> None:
    """Write metrics.json in the format expected by the Streamlit dashboard."""
    dashboard_metrics = format_dashboard_metrics(eval_result)
    for metrics_dir in (artifacts_dir, figures_dir):
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = metrics_dir / "metrics.json"
        with metrics_path.open("w", encoding="utf-8") as fh:
            json.dump(dashboard_metrics, fh, indent=2)
        log.info("Dashboard metrics.json saved to %s", metrics_path)


def _resolve_manifest_path(cli_manifest: str | None, manifests_dir: Path) -> Path:
    if cli_manifest:
        return Path(cli_manifest)

    candidates = [
        manifests_dir / "crop_manifest.csv",
        manifests_dir / "crop_manifest_small.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    config = load_config()
    path_map = ensure_project_dirs(config)
    training_cfg = config.get("training", {})

    manifest_path = _resolve_manifest_path(args.manifest, path_map["manifests_dir"])
    batch_size = args.batch_size or int(training_cfg.get("batch_size", 16))
    num_workers = (
        args.num_workers
        if args.num_workers is not None
        else int(training_cfg.get("num_workers", 2))
    )
    checkpoint_path = Path(args.checkpoint)
    seed = int(config.get("project", {}).get("random_seed", 42))

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
        artifacts_dir=path_map["artifacts_dir"],
        figures_dir=path_map["figures_dir"],
        max_samples=args.max_samples,
        seed=seed,
    )

    results_path = path_map["figures_dir"] / f"eval_results_{args.split}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    log.info("Evaluation results saved to %s", results_path)

    _write_dashboard_metrics(
        result,
        artifacts_dir=path_map["artifacts_dir"],
        figures_dir=path_map["figures_dir"],
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
