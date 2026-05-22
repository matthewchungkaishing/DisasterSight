"""Generate cached building predictions and scene summaries for the dashboard."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from src.common.paths import ensure_project_dirs, load_config
from src.inference.prediction_cache import (
    build_prediction_records,
    filter_crop_rows,
    read_crop_manifest,
    summarise_scene_predictions,
    write_prediction_csv,
    write_scene_summary_csv,
)
from src.models.classifier import PairedCropClassifier
from src.models.crop_dataset import CropDataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache model predictions for Streamlit.")
    parser.add_argument(
        "--checkpoint", required=True, help="Path to trained classifier checkpoint."
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
        help="Manifest split to cache.",
    )
    parser.add_argument(
        "--scene-id",
        action="append",
        default=None,
        help="Scene id to include. Repeat to include multiple scenes.",
    )
    parser.add_argument("--scene-limit", type=int, default=None, help="Maximum number of scenes.")
    parser.add_argument(
        "--batch-size", type=int, default=None, help="Override inference batch size."
    )
    parser.add_argument("--predictions-name", default=None, help="Output prediction CSV filename.")
    parser.add_argument("--summary-name", default=None, help="Output scene summary CSV filename.")
    return parser.parse_args()


def generate_cached_predictions(args: argparse.Namespace) -> tuple[Path, Path]:
    config = load_config()
    path_map = ensure_project_dirs(config)
    training_cfg = config.get("training", {})
    inference_cfg = config.get("inference", {})
    priority_cfg = config.get("priority_score", {})

    manifest_path = (
        Path(args.manifest) if args.manifest else path_map["manifests_dir"] / "crop_manifest.csv"
    )
    checkpoint_path = Path(args.checkpoint)
    batch_size = args.batch_size or int(training_cfg.get("batch_size", 16))
    num_workers = int(training_cfg.get("num_workers", 2))
    confidence_threshold = float(inference_cfg.get("confidence_threshold", 0.6))

    if not manifest_path.exists():
        raise FileNotFoundError(f"Crop manifest not found: {manifest_path}")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    all_rows = read_crop_manifest(manifest_path)
    selected_rows = filter_crop_rows(
        all_rows,
        split=args.split,
        scene_ids=set(args.scene_id) if args.scene_id else None,
        scene_limit=args.scene_limit,
    )
    if not selected_rows:
        raise ValueError("No crop rows matched the requested split/scene filters.")

    probabilities = _predict_probabilities(
        checkpoint_path=checkpoint_path,
        selected_rows=selected_rows,
        split=args.split,
        batch_size=batch_size,
        num_workers=num_workers,
    )
    prediction_records = build_prediction_records(
        selected_rows,
        probabilities,
        confidence_threshold=confidence_threshold,
    )
    summaries = summarise_scene_predictions(
        prediction_records,
        destroyed_weight=float(priority_cfg.get("destroyed_weight", 0.50)),
        major_damage_weight=float(priority_cfg.get("major_damage_weight", 0.30)),
        damage_density_weight=float(priority_cfg.get("damage_density_weight", 0.20)),
    )

    prediction_name = args.predictions_name or f"building_predictions_{args.split}.csv"
    summary_name = args.summary_name or f"scene_summaries_{args.split}.csv"
    prediction_path = path_map["predictions_dir"] / prediction_name
    summary_path = path_map["predictions_dir"] / summary_name
    write_prediction_csv(prediction_path, prediction_records)
    write_scene_summary_csv(summary_path, summaries)

    log.info("Cached %d building predictions: %s", len(prediction_records), prediction_path)
    log.info("Cached %d scene summaries: %s", len(summaries), summary_path)
    return prediction_path, summary_path


def _predict_probabilities(
    *,
    checkpoint_path: Path,
    selected_rows: list[dict[str, str]],
    split: str,
    batch_size: int,
    num_workers: int,
) -> list[list[float]]:
    """Run model inference and return probabilities aligned to selected_rows."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    saved_config = checkpoint.get("config", {})
    image_size = int(saved_config.get("image_size", 224))
    dropout = float(saved_config.get("dropout", 0.3))

    model = PairedCropClassifier(pretrained=False, dropout=dropout).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dataset = CropDataset(
        None,
        split=split,
        image_size=image_size,
        augment=False,
        records=selected_rows,
    )

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    probabilities: list[list[float]] = []
    with torch.no_grad():
        for inputs, _labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            probs = torch.softmax(model(inputs), dim=-1)
            probabilities.extend(probs.cpu().tolist())
    return probabilities


def main() -> int:
    args = parse_args()
    try:
        generate_cached_predictions(args)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
