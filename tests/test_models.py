"""Unit tests for the Phase 3 model package.

Tests cover:
  - CropDataset record loading and tensor shapes
  - Synchronized augmentation consistency
  - Class weight and sampler correctness
  - PairedCropClassifier forward pass and predict_proba
  - Checkpoint save/load round-trip
"""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import torch
from PIL import Image

from src.common.constants import CLASS_TO_INDEX, DAMAGE_CLASSES
from src.models.classifier import NUM_CLASSES, PAIRED_IN_CHANNELS, PairedCropClassifier
from src.models.crop_dataset import (
    CropDataset,
    class_distribution_summary,
    compute_class_weights,
    make_weighted_sampler,
    stratified_sample_records,
)


def _create_dummy_manifest(
    tmp_dir: Path,
    num_samples: int = 8,
    split: str = "train",
    image_size: int = 32,
) -> Path:
    """Create a minimal crop manifest with tiny dummy images on disk."""
    crops_dir = tmp_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_dir / "crop_manifest.csv"

    fieldnames = [
        "building_id",
        "scene_id",
        "disaster_name",
        "disaster_type",
        "split",
        "damage_label",
        "geometry_source",
        "polygon_xy",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "area_pixels",
        "crop_width",
        "crop_height",
        "pre_crop_path",
        "post_crop_path",
        "pre_masked_crop_path",
        "post_masked_crop_path",
    ]

    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(num_samples):
            label = DAMAGE_CLASSES[i % len(DAMAGE_CLASSES)]
            pre_path = crops_dir / f"building_{i}_pre.png"
            post_path = crops_dir / f"building_{i}_post.png"
            Image.new("RGB", (image_size, image_size), (i * 30, 100, 50)).save(pre_path)
            Image.new("RGB", (image_size, image_size), (50, i * 30, 100)).save(post_path)
            writer.writerow(
                {
                    "building_id": f"b_{i}",
                    "scene_id": f"scene_{i}",
                    "disaster_name": "test-disaster",
                    "disaster_type": "earthquake",
                    "split": split,
                    "damage_label": label,
                    "geometry_source": "polygon",
                    "polygon_xy": "[]",
                    "bbox_x1": 0,
                    "bbox_y1": 0,
                    "bbox_x2": image_size,
                    "bbox_y2": image_size,
                    "area_pixels": image_size * image_size,
                    "crop_width": image_size,
                    "crop_height": image_size,
                    "pre_crop_path": str(pre_path),
                    "post_crop_path": str(post_path),
                    "pre_masked_crop_path": "",
                    "post_masked_crop_path": "",
                }
            )

    return manifest_path


class TestClassWeights(unittest.TestCase):
    """Tests for inverse-frequency class weight computation."""

    def test_balanced_gives_equal_weights(self) -> None:
        labels = [0, 1, 2, 3] * 10
        weights = compute_class_weights(labels, num_classes=4)
        for w in weights:
            self.assertAlmostEqual(w.item(), 1.0, places=5)

    def test_imbalanced_upweights_minority(self) -> None:
        labels = [0] * 100 + [1] * 5 + [2] * 50 + [3] * 45
        weights = compute_class_weights(labels, num_classes=4)
        self.assertGreater(weights[1].item(), weights[0].item())
        self.assertGreater(weights[1].item(), weights[2].item())

    def test_empty_labels_returns_ones(self) -> None:
        weights = compute_class_weights([], num_classes=4)
        self.assertEqual(weights.tolist(), [1.0, 1.0, 1.0, 1.0])

    def test_missing_class_gets_high_weight(self) -> None:
        labels = [0, 0, 0, 2, 2, 2]
        weights = compute_class_weights(labels, num_classes=4)
        # Classes 1 and 3 have zero samples; they should get the largest weights.
        self.assertEqual(weights[1].item(), float(len(labels)))
        self.assertEqual(weights[3].item(), float(len(labels)))


class TestWeightedSampler(unittest.TestCase):
    def test_sampler_length_matches_dataset(self) -> None:
        labels = [0] * 100 + [1] * 5
        sampler = make_weighted_sampler(labels, num_classes=4)
        self.assertEqual(sampler.num_samples, len(labels))


class TestClassDistribution(unittest.TestCase):
    def test_summary_keys_match_damage_classes(self) -> None:
        labels = [0, 1, 2, 3, 0, 0]
        summary = class_distribution_summary(labels)
        self.assertEqual(set(summary.keys()), set(DAMAGE_CLASSES))
        self.assertEqual(summary["no_damage"], 3)
        self.assertEqual(summary["minor_damage"], 1)


class TestClassificationRollups(unittest.TestCase):
    def test_remap_confusion_matrix_merges_damage_classes(self) -> None:
        from src.common.classification_metrics import macro_scores, remap_confusion_matrix

        labels = [0, 1, 2, 3]
        preds = [0, 2, 1, 3]
        matrix = remap_confusion_matrix(
            labels,
            preds,
            class_mapping={0: 0, 1: 1, 2: 1, 3: 2},
            num_classes=3,
        )

        self.assertEqual(matrix, [[1, 0, 0], [0, 2, 0], [0, 0, 1]])
        self.assertAlmostEqual(macro_scores(matrix)[2], 1.0)

    def test_evaluation_rollups_include_binary_triage(self) -> None:
        from src.models.evaluate import _build_rollup_metrics

        rollups = _build_rollup_metrics(
            labels=[0, 1, 2, 3],
            preds=[0, 2, 1, 3],
        )

        self.assertIn("three_class", rollups)
        self.assertIn("binary_triage", rollups)
        self.assertEqual(rollups["three_class"]["macro_f1"], 1.0)
        self.assertEqual(
            rollups["binary_triage"]["classes"],
            ["no_low_damage", "significant_damage"],
        )


class TestTrainingGuardrails(unittest.TestCase):
    def test_low_class_counts_raise_by_default(self) -> None:
        from src.models.train import _class_count_guardrail

        with self.assertRaises(ValueError):
            _class_count_guardrail(
                {
                    "no_damage": 1000,
                    "minor_damage": 108,
                    "major_damage": 18,
                    "destroyed": 2,
                },
                {
                    "no_damage": 100,
                    "minor_damage": 9,
                    "major_damage": 9,
                    "destroyed": 23,
                },
                allow_low_class_counts=False,
            )

    def test_low_class_counts_can_be_allowed_for_smoke_runs(self) -> None:
        from src.models.train import _class_count_guardrail

        _class_count_guardrail(
            {
                "no_damage": 1000,
                "minor_damage": 108,
                "major_damage": 18,
                "destroyed": 2,
            },
            {
                "no_damage": 100,
                "minor_damage": 9,
                "major_damage": 9,
                "destroyed": 23,
            },
            allow_low_class_counts=True,
        )


class TestTrainingLosses(unittest.TestCase):
    def test_focal_loss_returns_scalar(self) -> None:
        from src.models.train import FocalLoss

        loss = FocalLoss(gamma=2.0, weight=torch.ones(4), label_smoothing=0.05)
        logits = torch.tensor([[3.0, 0.2, -0.1, -1.0], [0.1, 2.0, 0.3, -0.5]])
        labels = torch.tensor([0, 1])

        value = loss(logits, labels)

        self.assertEqual(value.ndim, 0)
        self.assertGreater(value.item(), 0.0)

    def test_build_loss_supports_configured_options(self) -> None:
        from src.models.train import FocalLoss, build_loss

        weights = torch.ones(4)
        self.assertIsInstance(
            build_loss(
                loss_function="cross_entropy",
                class_weights=weights,
                focal_gamma=2.0,
                label_smoothing=0.0,
            ),
            torch.nn.CrossEntropyLoss,
        )
        self.assertIsInstance(
            build_loss(
                loss_function="focal",
                class_weights=weights,
                focal_gamma=2.0,
                label_smoothing=0.05,
            ),
            FocalLoss,
        )


class TestStratifiedSampling(unittest.TestCase):
    def test_sample_keeps_available_classes(self) -> None:
        records = (
            [{"damage_label": "no_damage", "building_id": f"n{i}"} for i in range(20)]
            + [{"damage_label": "minor_damage", "building_id": "m1"}]
            + [{"damage_label": "major_damage", "building_id": "j1"}]
            + [{"damage_label": "destroyed", "building_id": "d1"}]
        )

        sampled = stratified_sample_records(records, 8, seed=7)
        labels = {record["damage_label"] for record in sampled}

        self.assertEqual(len(sampled), 8)
        self.assertEqual(labels, set(DAMAGE_CLASSES))


class TestCropDataset(unittest.TestCase):
    """Tests for the paired-crop dataset loader."""

    def test_loads_correct_split_and_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _create_dummy_manifest(Path(tmp), num_samples=8, split="train")
            dataset = CropDataset(
                manifest,
                split="train",
                image_size=32,
                augment=False,
                project_root=Path(tmp),
            )
            self.assertEqual(len(dataset), 8)

            tensor, label = dataset[0]
            self.assertEqual(tensor.shape, (6, 32, 32))
            self.assertIn(label, range(NUM_CLASSES))

    def test_empty_split_returns_zero_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _create_dummy_manifest(Path(tmp), num_samples=4, split="train")
            dataset = CropDataset(
                manifest,
                split="val",
                image_size=32,
                augment=False,
                project_root=Path(tmp),
            )
            self.assertEqual(len(dataset), 0)

    def test_augmented_dataset_still_produces_correct_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _create_dummy_manifest(Path(tmp), num_samples=4, split="train")
            dataset = CropDataset(
                manifest,
                split="train",
                image_size=64,
                augment=True,
                project_root=Path(tmp),
            )
            tensor, _ = dataset[0]
            self.assertEqual(tensor.shape, (6, 64, 64))

    def test_label_indices_match_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _create_dummy_manifest(Path(tmp), num_samples=8, split="train")
            dataset = CropDataset(
                manifest,
                split="train",
                image_size=32,
                augment=False,
                project_root=Path(tmp),
            )
            for i, idx in enumerate(dataset.label_indices):
                expected_label = DAMAGE_CLASSES[i % len(DAMAGE_CLASSES)]
                self.assertEqual(idx, CLASS_TO_INDEX[expected_label])

    def test_bad_path_raises_runtime_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _create_dummy_manifest(Path(tmp), num_samples=2, split="train")
            dataset = CropDataset(
                manifest,
                split="train",
                image_size=32,
                augment=False,
                project_root=Path(tmp),
            )
            # Corrupt a crop path on disk
            record = dataset._records[0]
            pre_path = Path(record["pre_crop_path"])
            pre_path.unlink()
            with self.assertRaises(RuntimeError):
                _ = dataset[0]


class TestPairedCropClassifier(unittest.TestCase):
    """Tests for the classifier model."""

    def test_forward_output_shape(self) -> None:
        model = PairedCropClassifier(pretrained=False, dropout=0.0)
        x = torch.randn(2, PAIRED_IN_CHANNELS, 32, 32)
        logits = model(x)
        self.assertEqual(logits.shape, (2, NUM_CLASSES))

    def test_predict_proba_sums_to_one(self) -> None:
        model = PairedCropClassifier(pretrained=False, dropout=0.0)
        x = torch.randn(3, PAIRED_IN_CHANNELS, 32, 32)
        probs = model.predict_proba(x)
        self.assertEqual(probs.shape, (3, NUM_CLASSES))
        for row in probs:
            self.assertAlmostEqual(row.sum().item(), 1.0, places=5)

    def test_predict_proba_restores_training_mode(self) -> None:
        model = PairedCropClassifier(pretrained=False)
        model.train()
        x = torch.randn(1, PAIRED_IN_CHANNELS, 32, 32)
        _ = model.predict_proba(x)
        self.assertTrue(model.training)

    def test_checkpoint_round_trip(self) -> None:
        model = PairedCropClassifier(pretrained=False, dropout=0.1)
        model.eval()
        x = torch.randn(1, PAIRED_IN_CHANNELS, 64, 64)
        original_output = model(x).detach()

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            checkpoint_path = Path(f.name)

        torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)

        loaded_model = PairedCropClassifier(pretrained=False, dropout=0.1)
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        loaded_model.load_state_dict(state["model_state_dict"])
        loaded_model.eval()

        loaded_output = loaded_model(x).detach()
        self.assertTrue(torch.allclose(original_output, loaded_output, atol=1e-5))

        checkpoint_path.unlink()


if __name__ == "__main__":
    unittest.main()
