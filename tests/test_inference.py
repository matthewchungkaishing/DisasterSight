from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.inference.prediction_cache import (
    build_prediction_records,
    filter_crop_rows,
    summarise_scene_predictions,
    write_prediction_csv,
    write_scene_summary_csv,
)


def _crop_row(
    building_id: str,
    scene_id: str,
    split: str = "test",
) -> dict[str, str]:
    return {
        "building_id": building_id,
        "scene_id": scene_id,
        "disaster_name": "demo-event",
        "disaster_type": "earthquake",
        "split": split,
        "damage_label": "major_damage",
        "polygon_xy": "[[0,0],[4,0],[4,4],[0,4]]",
        "bbox_x1": "0",
        "bbox_y1": "0",
        "bbox_x2": "4",
        "bbox_y2": "4",
        "pre_crop_path": f"data/interim/crops/{scene_id}/{building_id}_pre.png",
        "post_crop_path": f"data/interim/crops/{scene_id}/{building_id}_post.png",
    }


class PredictionCacheTests(unittest.TestCase):
    def test_filter_crop_rows_keeps_requested_split_and_scene_limit(self) -> None:
        rows = [
            _crop_row("a", "scene-1", "train"),
            _crop_row("b", "scene-1", "test"),
            _crop_row("c", "scene-2", "test"),
            _crop_row("d", "scene-3", "test"),
        ]

        selected = filter_crop_rows(rows, split="test", scene_limit=2)

        self.assertEqual([row["building_id"] for row in selected], ["b", "c"])

    def test_build_prediction_records_flags_low_confidence(self) -> None:
        rows = [_crop_row("a", "scene-1"), _crop_row("b", "scene-1")]
        probabilities = [
            [0.1, 0.2, 0.65, 0.05],
            [0.25, 0.2, 0.3, 0.25],
        ]

        records = build_prediction_records(rows, probabilities, confidence_threshold=0.6)

        self.assertEqual(records[0].predicted_label, "major_damage")
        self.assertFalse(records[0].needs_review)
        self.assertEqual(records[1].predicted_label, "major_damage")
        self.assertTrue(records[1].needs_review)
        self.assertEqual(json.loads(records[0].class_probabilities)["major_damage"], 0.65)

    def test_scene_summary_computes_counts_priority_and_review_flags(self) -> None:
        rows = [
            _crop_row("a", "scene-1"),
            _crop_row("b", "scene-1"),
            _crop_row("c", "scene-1"),
            _crop_row("d", "scene-1"),
        ]
        probabilities = [
            [0.9, 0.05, 0.03, 0.02],
            [0.05, 0.1, 0.8, 0.05],
            [0.05, 0.05, 0.1, 0.8],
            [0.05, 0.4, 0.3, 0.25],
        ]
        records = build_prediction_records(rows, probabilities, confidence_threshold=0.6)

        summaries = summarise_scene_predictions(
            records,
            destroyed_weight=0.50,
            major_damage_weight=0.30,
            damage_density_weight=0.20,
        )

        self.assertEqual(len(summaries), 1)
        summary = summaries[0]
        self.assertEqual(json.loads(summary.class_counts)["destroyed"], 1)
        self.assertEqual(summary.review_flag_count, 1)
        self.assertEqual(summary.priority_score, 35.0)

    def test_write_prediction_and_summary_csvs(self) -> None:
        rows = [_crop_row("a", "scene-1")]
        records = build_prediction_records(
            rows,
            [[0.7, 0.1, 0.1, 0.1]],
            confidence_threshold=0.6,
        )
        summaries = summarise_scene_predictions(
            records,
            destroyed_weight=0.50,
            major_damage_weight=0.30,
            damage_density_weight=0.20,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            prediction_path = Path(temp_dir) / "building_predictions.csv"
            summary_path = Path(temp_dir) / "scene_summaries.csv"
            write_prediction_csv(prediction_path, records)
            write_scene_summary_csv(summary_path, summaries)

            with prediction_path.open("r", encoding="utf-8", newline="") as handle:
                prediction_rows = list(csv.DictReader(handle))
            with summary_path.open("r", encoding="utf-8", newline="") as handle:
                summary_rows = list(csv.DictReader(handle))

        self.assertEqual(prediction_rows[0]["predicted_label"], "no_damage")
        self.assertEqual(summary_rows[0]["scene_id"], "scene-1")


if __name__ == "__main__":
    unittest.main()
