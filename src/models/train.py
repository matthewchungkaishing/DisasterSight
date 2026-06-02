"""Phase 3 training script: baseline paired-image damage classifier.

Usage:
    python -m src.models.train
    python -m src.models.train --manifest artifacts/manifests/crop_manifest.csv
    python -m src.models.train --max-epochs 5 --batch-size 8

All defaults come from config.yaml.  CLI flags override individual settings.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.common.classification_metrics import (
    confusion_matrix_counts,
    macro_scores,
    per_class_precision_recall_f1,
)
from src.common.constants import DAMAGE_CLASSES
from src.common.paths import ensure_project_dirs, load_config
from src.models.classifier import PairedCropClassifier
from src.models.crop_dataset import (
    NUM_CLASSES,
    CropDataset,
    class_distribution_summary,
    compute_class_weights,
    load_crop_records,
    make_weighted_sampler,
    stratified_sample_records,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


def seed_everything(seed: int) -> None:
    """Pin all random sources so runs are reproducible on the same hardware."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the baseline damage classifier.")
    parser.add_argument("--manifest", default=None, help="Path to crop manifest CSV.")
    parser.add_argument("--checkpoint-dir", default=None, help="Directory for saved checkpoints.")
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--image-size", type=int, default=None)
    parser.add_argument("--num-workers", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument(
        "--class-weight-strategy",
        choices=["loss_weight", "sampler", "both", "none"],
        default=None,
        help="How to address class imbalance (default from config.yaml).",
    )
    parser.add_argument(
        "--loss-function",
        choices=["cross_entropy", "focal"],
        default=None,
        help="Classification loss to use (default from config.yaml).",
    )
    parser.add_argument(
        "--focal-gamma",
        type=float,
        default=None,
        help="Focusing strength for focal loss. Only used with focal loss.",
    )
    parser.add_argument(
        "--label-smoothing",
        type=float,
        default=None,
        help="Label smoothing passed to the classification loss.",
    )
    parser.add_argument("--no-pretrained", action="store_true", help="Disable pretrained backbone.")
    parser.add_argument("--seed", type=int, default=None, help="Override random seed.")
    parser.add_argument(
        "--max-train-samples",
        type=int,
        default=None,
        help="Class-aware cap for train rows. Intended for CPU smoke runs on real xBD crops.",
    )
    parser.add_argument(
        "--max-val-samples",
        type=int,
        default=None,
        help="Class-aware cap for validation rows. Intended for CPU smoke runs on real xBD crops.",
    )
    parser.add_argument(
        "--allow-low-class-counts",
        action="store_true",
        help="Allow training when one or more damage classes has too few samples. Smoke runs only.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
    *,
    training: bool,
    max_grad_norm: float = 1.0,
) -> tuple[float, list[int], list[int]]:
    """Run one pass through the dataloader.  Returns (mean_loss, all_preds, all_labels)."""
    model.train(training)
    total_loss = 0.0
    num_samples = 0
    all_preds: list[int] = []
    all_labels: list[int] = []

    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            logits = model(inputs)
            loss = criterion(logits, labels)

            if training and optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()

            batch_size = inputs.size(0)
            total_loss += loss.item() * batch_size
            num_samples += batch_size
            all_preds.extend(logits.detach().argmax(dim=1).cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    mean_loss = total_loss / max(num_samples, 1)
    return mean_loss, all_preds, all_labels


def _macro_f1(preds: list[int], labels: list[int]) -> float:
    matrix = confusion_matrix_counts(labels, preds, num_classes=NUM_CLASSES)
    return macro_scores(matrix)[2]


class FocalLoss(nn.Module):
    """Weighted multi-class focal loss for class-imbalanced crop classification."""

    def __init__(
        self,
        *,
        gamma: float = 2.0,
        weight: torch.Tensor | None = None,
        label_smoothing: float = 0.0,
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight)
        self.label_smoothing = label_smoothing

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        ce_loss = nn.functional.cross_entropy(
            logits,
            labels,
            weight=self.weight,
            reduction="none",
            label_smoothing=self.label_smoothing,
        )
        true_class_prob = torch.softmax(logits, dim=1).gather(1, labels.unsqueeze(1)).squeeze(1)
        focal_factor = (1.0 - true_class_prob).clamp(min=0.0).pow(self.gamma)
        return (focal_factor * ce_loss).mean()


def build_loss(
    *,
    loss_function: str,
    class_weights: torch.Tensor | None,
    focal_gamma: float,
    label_smoothing: float,
) -> nn.Module:
    """Construct the configured classification loss."""
    if loss_function == "cross_entropy":
        return nn.CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing)
    if loss_function == "focal":
        return FocalLoss(
            gamma=focal_gamma,
            weight=class_weights,
            label_smoothing=label_smoothing,
        )
    raise ValueError(f"Unsupported loss function: {loss_function}")


def _log_metrics(
    phase: str,
    epoch: int,
    loss: float,
    preds: list[int],
    labels: list[int],
) -> dict[str, float | str | int]:
    matrix = confusion_matrix_counts(labels, preds, num_classes=NUM_CLASSES)
    macro = macro_scores(matrix)[2]
    _precision, _recall, per_class = per_class_precision_recall_f1(matrix)
    per_class_str = "  ".join(f"{DAMAGE_CLASSES[i]}={per_class[i]:.3f}" for i in range(NUM_CLASSES))
    log.info(
        "%s  epoch %02d  loss=%.4f  macro_f1=%.4f  %s",
        phase.upper(),
        epoch,
        loss,
        macro,
        per_class_str,
    )
    row: dict[str, float | str | int] = {
        "epoch": epoch,
        "phase": phase,
        "loss": loss,
        "macro_f1": macro,
    }
    for i in range(NUM_CLASSES):
        row[f"f1_{DAMAGE_CLASSES[i]}"] = float(per_class[i])
    return row


def _class_count_guardrail(
    train_counts: dict[str, int],
    val_counts: dict[str, int],
    *,
    allow_low_class_counts: bool,
    min_train_per_class: int = 50,
    min_val_per_class: int = 5,
) -> None:
    """Fail fast when a manifest cannot support credible 4-class training."""
    low_train = {
        label: count for label, count in train_counts.items() if count < min_train_per_class
    }
    low_val = {label: count for label, count in val_counts.items() if count < min_val_per_class}
    if not low_train and not low_val:
        return

    message = (
        "Manifest class coverage is too low for credible 4-class training. "
        f"Minimum train samples per class: {min_train_per_class}; "
        f"minimum val samples per class: {min_val_per_class}. "
        f"Low train counts: {low_train or 'none'}. "
        f"Low val counts: {low_val or 'none'}. "
        "Use a better-balanced manifest such as crop_manifest_focus.csv, or pass "
        "--allow-low-class-counts only for a deliberate smoke run."
    )
    if allow_low_class_counts:
        log.warning("%s", message)
        return
    raise ValueError(message)


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------


def train(args: argparse.Namespace) -> Path:
    config = load_config()
    path_map = ensure_project_dirs(config)
    training_cfg = config.get("training", {})
    dataset_cfg = config.get("dataset", {})
    project_cfg = config.get("project", {})

    # Reproducibility
    seed = args.seed if args.seed is not None else int(project_cfg.get("random_seed", 42))
    seed_everything(seed)
    log.info("Random seed: %d", seed)

    # Resolve paths
    manifest_path = _resolve_manifest_path(args.manifest, path_map["manifests_dir"])
    checkpoint_dir = (
        Path(args.checkpoint_dir) if args.checkpoint_dir else path_map["checkpoints_dir"]
    )
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Hyperparameters — CLI overrides config
    max_epochs: int = args.max_epochs or int(training_cfg.get("max_epochs", 10))
    batch_size: int = args.batch_size or int(training_cfg.get("batch_size", 16))
    learning_rate: float = args.learning_rate or float(training_cfg.get("learning_rate", 3e-4))
    patience: int = int(training_cfg.get("early_stopping_patience", 3))
    image_size: int = args.image_size or int(dataset_cfg.get("image_size", 224))
    num_workers: int = (
        args.num_workers
        if args.num_workers is not None
        else int(training_cfg.get("num_workers", 2))
    )
    strategy: str = args.class_weight_strategy or training_cfg.get(
        "class_weight_strategy", "loss_weight"
    )
    loss_function: str = args.loss_function or training_cfg.get("loss_function", "cross_entropy")
    focal_gamma: float = (
        args.focal_gamma
        if args.focal_gamma is not None
        else float(training_cfg.get("focal_gamma", 2.0))
    )
    label_smoothing: float = (
        args.label_smoothing
        if args.label_smoothing is not None
        else float(training_cfg.get("label_smoothing", 0.0))
    )
    dropout: float = float(training_cfg.get("dropout", 0.3))
    pretrained: bool = not args.no_pretrained

    log.info("Manifest: %s", manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Crop manifest not found: {manifest_path}\n"
            "Run `python -m src.data.build_crop_manifest` first."
        )

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------
    train_records = stratified_sample_records(
        load_crop_records(manifest_path, "train"),
        args.max_train_samples,
        seed=seed,
    )
    val_records = stratified_sample_records(
        load_crop_records(manifest_path, "val"),
        args.max_val_samples,
        seed=seed + 1,
    )
    train_dataset = CropDataset(
        None,
        split="train",
        image_size=image_size,
        augment=True,
        records=train_records,
    )
    val_dataset = CropDataset(
        None,
        split="val",
        image_size=image_size,
        augment=False,
        records=val_records,
    )

    train_counts = class_distribution_summary(train_dataset.label_indices)
    val_counts = class_distribution_summary(val_dataset.label_indices)

    log.info(
        "Train samples: %d  distribution: %s",
        len(train_dataset),
        train_counts,
    )
    log.info(
        "Val   samples: %d  distribution: %s",
        len(val_dataset),
        val_counts,
    )

    if len(train_dataset) == 0:
        raise ValueError("Train split is empty. Check manifest split assignments.")
    if len(val_dataset) == 0:
        raise ValueError("Val split is empty. Check manifest split assignments.")
    _class_count_guardrail(
        train_counts,
        val_counts,
        allow_low_class_counts=args.allow_low_class_counts,
    )

    # ------------------------------------------------------------------
    # Class-imbalance handling
    # ------------------------------------------------------------------
    use_loss_weight = strategy in ("loss_weight", "both")
    use_sampler = strategy in ("sampler", "both")

    class_weights: torch.Tensor | None = None
    if use_loss_weight:
        class_weights = compute_class_weights(train_dataset.label_indices, NUM_CLASSES)
        log.info(
            "Class loss weights: %s",
            dict(zip(DAMAGE_CLASSES, [round(w, 4) for w in class_weights.tolist()], strict=True)),
        )

    train_sampler = None
    if use_sampler:
        train_sampler = make_weighted_sampler(train_dataset.label_indices, NUM_CLASSES)
        log.info("Using WeightedRandomSampler for balanced training batches.")

    # ------------------------------------------------------------------
    # DataLoaders
    # ------------------------------------------------------------------
    use_cuda = torch.cuda.is_available()
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=train_sampler,
        shuffle=(train_sampler is None),
        num_workers=num_workers,
        pin_memory=use_cuda,
        drop_last=(len(train_dataset) > batch_size),
        persistent_workers=(num_workers > 0),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=use_cuda,
        persistent_workers=(num_workers > 0),
    )

    # ------------------------------------------------------------------
    # Model, loss, optimiser
    # ------------------------------------------------------------------
    device = torch.device("cuda" if use_cuda else "cpu")
    log.info("Device: %s", device)

    model = PairedCropClassifier(pretrained=pretrained, dropout=dropout).to(device)
    weight_tensor = class_weights.to(device) if class_weights is not None else None
    criterion = build_loss(
        loss_function=loss_function,
        class_weights=weight_tensor,
        focal_gamma=focal_gamma,
        label_smoothing=label_smoothing,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)

    # ------------------------------------------------------------------
    # Training loop — early stopping on val macro F1
    # ------------------------------------------------------------------
    best_macro_f1 = -1.0
    epochs_without_improvement = 0
    best_checkpoint_path = checkpoint_dir / "best_classifier.pt"
    log_rows: list[dict] = []
    run_id = int(time.time())

    run_config = {
        "seed": seed,
        "max_epochs": max_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "image_size": image_size,
        "class_weight_strategy": strategy,
        "loss_function": loss_function,
        "focal_gamma": focal_gamma,
        "label_smoothing": label_smoothing,
        "dropout": dropout,
        "pretrained": pretrained,
    }
    log.info("Starting training: %s", run_config)

    for epoch in range(1, max_epochs + 1):
        train_loss, train_preds, train_labels = _run_epoch(
            model,
            train_loader,
            criterion,
            optimizer,
            device,
            training=True,
        )
        val_loss, val_preds, val_labels = _run_epoch(
            model,
            val_loader,
            criterion,
            None,
            device,
            training=False,
        )
        scheduler.step()

        train_row = _log_metrics("train", epoch, train_loss, train_preds, train_labels)
        val_row = _log_metrics("val", epoch, val_loss, val_preds, val_labels)
        log_rows.extend([train_row, val_row])

        val_macro_f1 = float(val_row["macro_f1"])
        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            epochs_without_improvement = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "val_macro_f1": best_macro_f1,
                    "config": run_config,
                    "class_names": list(DAMAGE_CLASSES),
                },
                best_checkpoint_path,
            )
            log.info(
                "  -> New best val macro_f1=%.4f saved to %s",
                best_macro_f1,
                best_checkpoint_path,
            )
        else:
            epochs_without_improvement += 1
            log.info("  No improvement (%d/%d).", epochs_without_improvement, patience)
            if epochs_without_improvement >= patience:
                log.info("Early stopping triggered at epoch %d.", epoch)
                break

    # ------------------------------------------------------------------
    # Save training log
    # ------------------------------------------------------------------
    log_path = checkpoint_dir / f"train_log_{run_id}.csv"
    if log_rows:
        with log_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
            writer.writeheader()
            writer.writerows(log_rows)
        log.info("Training log saved to %s", log_path)

    # ------------------------------------------------------------------
    # Final confusion matrix on val using best checkpoint
    # ------------------------------------------------------------------
    checkpoint = torch.load(best_checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    _, final_preds, final_labels = _run_epoch(
        model,
        val_loader,
        criterion,
        None,
        device,
        training=False,
    )
    cm = confusion_matrix_counts(final_labels, final_preds, num_classes=NUM_CLASSES)
    log.info("Validation confusion matrix (rows=true, cols=predicted):")
    log.info("Classes: %s", " | ".join(DAMAGE_CLASSES))
    for i, cm_row in enumerate(cm):
        log.info("  %s: %s", DAMAGE_CLASSES[i], cm_row)

    cm_path = checkpoint_dir / f"val_confusion_matrix_{run_id}.json"
    with cm_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"classes": list(DAMAGE_CLASSES), "matrix": cm},
            f,
            indent=2,
        )
    log.info("Confusion matrix saved to %s", cm_path)
    log.info(
        "Done.  Best val macro_f1=%.4f  Checkpoint: %s",
        best_macro_f1,
        best_checkpoint_path,
    )
    return best_checkpoint_path


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


def main() -> int:
    args = parse_args()
    try:
        train(args)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
