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
from sklearn.metrics import confusion_matrix, f1_score
from torch.utils.data import DataLoader

from src.common.constants import DAMAGE_CLASSES
from src.common.paths import ensure_project_dirs, load_config
from src.models.classifier import PairedCropClassifier
from src.models.crop_dataset import (
    NUM_CLASSES,
    CropDataset,
    class_distribution_summary,
    compute_class_weights,
    make_weighted_sampler,
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
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument(
        "--class-weight-strategy",
        choices=["loss_weight", "sampler", "both", "none"],
        default=None,
        help="How to address class imbalance (default from config.yaml).",
    )
    parser.add_argument("--no-pretrained", action="store_true", help="Disable pretrained backbone.")
    parser.add_argument("--seed", type=int, default=None, help="Override random seed.")
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
    return float(
        f1_score(
            labels,
            preds,
            average="macro",
            zero_division=0,
            labels=list(range(NUM_CLASSES)),
        )
    )


def _log_metrics(
    phase: str,
    epoch: int,
    loss: float,
    preds: list[int],
    labels: list[int],
) -> dict[str, float | str | int]:
    macro = _macro_f1(preds, labels)
    per_class = f1_score(
        labels,
        preds,
        average=None,
        zero_division=0,
        labels=list(range(NUM_CLASSES)),
    )
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
    manifest_path = (
        Path(args.manifest) if args.manifest else path_map["manifests_dir"] / "crop_manifest.csv"
    )
    checkpoint_dir = (
        Path(args.checkpoint_dir) if args.checkpoint_dir else path_map["checkpoints_dir"]
    )
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Hyperparameters — CLI overrides config
    max_epochs: int = args.max_epochs or int(training_cfg.get("max_epochs", 10))
    batch_size: int = args.batch_size or int(training_cfg.get("batch_size", 16))
    learning_rate: float = args.learning_rate or float(training_cfg.get("learning_rate", 3e-4))
    patience: int = int(training_cfg.get("early_stopping_patience", 3))
    image_size: int = int(dataset_cfg.get("image_size", 224))
    num_workers: int = int(training_cfg.get("num_workers", 2))
    strategy: str = args.class_weight_strategy or training_cfg.get(
        "class_weight_strategy", "loss_weight"
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
    train_dataset = CropDataset(
        manifest_path,
        split="train",
        image_size=image_size,
        augment=True,
    )
    val_dataset = CropDataset(
        manifest_path,
        split="val",
        image_size=image_size,
        augment=False,
    )

    log.info(
        "Train samples: %d  distribution: %s",
        len(train_dataset),
        class_distribution_summary(train_dataset.label_indices),
    )
    log.info(
        "Val   samples: %d  distribution: %s",
        len(val_dataset),
        class_distribution_summary(val_dataset.label_indices),
    )

    if len(train_dataset) == 0:
        raise ValueError("Train split is empty. Check manifest split assignments.")
    if len(val_dataset) == 0:
        raise ValueError("Val split is empty. Check manifest split assignments.")

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
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
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
    cm = confusion_matrix(final_labels, final_preds, labels=list(range(NUM_CLASSES)))
    log.info("Validation confusion matrix (rows=true, cols=predicted):")
    log.info("Classes: %s", " | ".join(DAMAGE_CLASSES))
    for i, cm_row in enumerate(cm):
        log.info("  %s: %s", DAMAGE_CLASSES[i], cm_row.tolist())

    cm_path = checkpoint_dir / f"val_confusion_matrix_{run_id}.json"
    with cm_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"classes": list(DAMAGE_CLASSES), "matrix": cm.tolist()},
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
