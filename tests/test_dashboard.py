"""Tests for dashboard pure-logic modules.

Tests cover :mod:`labels`, :mod:`priority`, :mod:`artifact_resolver`,
and :mod:`overlays` — all the modules that can be exercised without a
running Streamlit server.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import numpy as np
from PIL import Image


class TestLabels(unittest.TestCase):
    """Label normalization and display helpers."""

    def test_normalize_xbd_hyphenated(self) -> None:
        from src.dashboard.labels import normalize_label

        self.assertEqual(normalize_label("no-damage"), "no_damage")
        self.assertEqual(normalize_label("minor-damage"), "minor_damage")
        self.assertEqual(normalize_label("major-damage"), "major_damage")
        self.assertEqual(normalize_label("destroyed"), "destroyed")
        self.assertEqual(normalize_label("un-classified"), "unclassified")

    def test_normalize_already_canonical(self) -> None:
        from src.dashboard.labels import normalize_label

        for label in ("no_damage", "minor_damage", "major_damage", "destroyed"):
            self.assertEqual(normalize_label(label), label)

    def test_normalize_none_and_empty(self) -> None:
        from src.dashboard.labels import normalize_label

        self.assertEqual(normalize_label(None), "unknown")
        self.assertEqual(normalize_label(""), "unknown")

    def test_normalize_case_insensitive(self) -> None:
        from src.dashboard.labels import normalize_label

        self.assertEqual(normalize_label("No-Damage"), "no_damage")
        self.assertEqual(normalize_label("DESTROYED"), "destroyed")

    def test_normalize_whitespace_variants(self) -> None:
        from src.dashboard.labels import normalize_label

        self.assertEqual(normalize_label("  no damage "), "no_damage")
        self.assertEqual(normalize_label("major damage"), "major_damage")

    def test_display_label_canonical(self) -> None:
        from src.dashboard.labels import display_label

        self.assertEqual(display_label("no_damage"), "NO DAMAGE")
        self.assertEqual(display_label("destroyed"), "DESTROYED")
        self.assertEqual(display_label("review_required"), "REVIEW REQUIRED")

    def test_display_label_hyphenated(self) -> None:
        from src.dashboard.labels import display_label

        self.assertEqual(display_label("major-damage"), "MAJOR")

    def test_badge_class_known(self) -> None:
        from src.dashboard.labels import badge_class

        self.assertEqual(badge_class("destroyed"), "destroyed")
        self.assertEqual(badge_class("no_damage"), "no_damage")

    def test_badge_class_unknown_defaults_to_review(self) -> None:
        from src.dashboard.labels import badge_class

        self.assertEqual(badge_class("some_weird_label"), "review_required")


class TestPriority(unittest.TestCase):
    """Priority score computation and zone-summary builder."""

    def test_compute_shares_all_destroyed(self) -> None:
        from src.dashboard.priority import compute_shares

        counts = {"no_damage": 0, "minor_damage": 0, "major_damage": 0, "destroyed": 10}
        shares = compute_shares(counts, 10)
        self.assertAlmostEqual(shares["destroyed_share"], 1.0)
        self.assertAlmostEqual(shares["damage_density"], 1.0)

    def test_compute_shares_zero_total(self) -> None:
        from src.dashboard.priority import compute_shares

        shares = compute_shares({}, 0)
        self.assertEqual(shares["destroyed_share"], 0.0)
        self.assertEqual(shares["damage_density"], 0.0)

    def test_compute_shares_mixed(self) -> None:
        from src.dashboard.priority import compute_shares

        counts = {"no_damage": 5, "minor_damage": 2, "major_damage": 2, "destroyed": 1}
        shares = compute_shares(counts, 10)
        self.assertAlmostEqual(shares["destroyed_share"], 0.1)
        self.assertAlmostEqual(shares["major_damage_share"], 0.2)
        self.assertAlmostEqual(shares["damage_density"], 0.5)

    def test_compute_priority_score_max(self) -> None:
        from src.dashboard.priority import compute_priority_score

        weights = {"destroyed": 0.5, "major_damage": 0.3, "damage_density": 0.2}
        score = compute_priority_score(1.0, 1.0, 1.0, weights=weights)
        self.assertAlmostEqual(score, 100.0)

    def test_compute_priority_score_zero(self) -> None:
        from src.dashboard.priority import compute_priority_score

        weights = {"destroyed": 0.5, "major_damage": 0.3, "damage_density": 0.2}
        score = compute_priority_score(0.0, 0.0, 0.0, weights=weights)
        self.assertAlmostEqual(score, 0.0)

    def test_build_zone_summary_shape(self) -> None:
        from src.dashboard.priority import build_zone_summary

        counts = {"no_damage": 3, "destroyed": 7}
        summary = build_zone_summary("scene_001", counts, review_flag_count=2)
        self.assertEqual(summary["scene_id"], "scene_001")
        self.assertEqual(summary["total_buildings"], 10)
        self.assertEqual(summary["review_flag_count"], 2)
        self.assertIn("priority_score", summary)
        self.assertIn("class_counts", summary)

    def test_priority_css_class(self) -> None:
        from src.dashboard.priority import priority_css_class

        self.assertEqual(priority_css_class(90), "ds-priority-high")
        self.assertEqual(priority_css_class(60), "ds-priority-mid")
        self.assertEqual(priority_css_class(30), "ds-priority-low")

    def test_rationale_text_contains_scene(self) -> None:
        from src.dashboard.priority import rationale_text

        summary = {
            "scene_id": "test_scene",
            "priority_score": 85,
            "destroyed_share": 0.5,
            "major_damage_share": 0.3,
        }
        text = rationale_text(summary, "Test Disaster")
        self.assertIn("test_scene", text)
        self.assertIn("Test Disaster", text)
        self.assertIn("Human verification", text)


class TestArtifactResolver(unittest.TestCase):
    """Pure artifact resolution and I/O tests."""

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def test_resolve_scenes_from_json(self) -> None:
        from src.dashboard.artifact_resolver import resolve_scenes

        with tempfile.TemporaryDirectory() as tmpdir:
            processed = Path(tmpdir) / "data" / "processed"
            scenes_file = processed / "scenes.json"
            scenes_data = [{"scene_id": "test_001", "disaster_name": "Test"}]
            self._write_json(scenes_file, scenes_data)

            paths = {"processed_data_dir": processed}
            records, is_fixture = resolve_scenes(paths=paths)
            self.assertFalse(is_fixture)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["scene_id"], "test_001")

    def test_resolve_scenes_fixture_fallback(self) -> None:
        from src.dashboard.artifact_resolver import resolve_scenes

        paths = {"processed_data_dir": Path("/nonexistent"), "manifests_dir": Path("/nonexistent")}
        records, is_fixture = resolve_scenes(paths=paths)
        self.assertTrue(is_fixture)
        self.assertGreater(len(records), 0)

    def test_resolve_predictions_from_jsonl(self) -> None:
        from src.dashboard.artifact_resolver import resolve_predictions

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            rows = [
                {"scene_id": "s1", "building_id": "b1", "predicted_label": "destroyed"},
                {"scene_id": "s2", "building_id": "b2", "predicted_label": "no_damage"},
            ]
            self._write_jsonl(pred_dir / "s1.jsonl", rows)
            paths = {"predictions_dir": pred_dir}
            result = resolve_predictions("s1", paths=paths)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["building_id"], "b1")

    def test_resolve_predictions_from_json(self) -> None:
        from src.dashboard.artifact_resolver import resolve_predictions

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            data = [
                {"scene_id": "s1", "building_id": "b1", "predicted_label": "destroyed"},
                {"scene_id": "s1", "building_id": "b2", "predicted_label": "no_damage"},
            ]
            self._write_json(pred_dir / "s1.json", data)
            paths = {"predictions_dir": pred_dir}
            result = resolve_predictions("s1", paths=paths)
            self.assertEqual(len(result), 2)

    def test_resolve_metrics_fixture_fallback(self) -> None:
        from src.dashboard.artifact_resolver import resolve_metrics

        paths = {"artifacts_dir": Path("/nonexistent"), "figures_dir": Path("/nonexistent")}
        metrics = resolve_metrics(paths=paths)
        self.assertIn("macro_f1", metrics)

    def test_resolve_zone_summaries_fixture_fallback(self) -> None:
        from src.dashboard.artifact_resolver import resolve_zone_summaries

        paths = {"artifacts_dir": Path("/nonexistent"), "processed_data_dir": Path("/nonexistent")}
        records, is_fixture = resolve_zone_summaries(paths=paths)
        self.assertTrue(is_fixture)
        self.assertGreater(len(records), 0)
        scores = [r.get("priority_score", 0) for r in records]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_resolve_image_path_missing(self) -> None:
        from src.dashboard.artifact_resolver import resolve_image_path

        self.assertIsNone(resolve_image_path(""))
        self.assertIsNone(resolve_image_path("data/nonexistent/image.png"))

    def test_scene_image_sources_local_preferred(self) -> None:
        from src.dashboard.artifact_resolver import scene_image_sources

        with tempfile.TemporaryDirectory() as tmpdir:
            pre = Path(tmpdir) / "pre.png"
            post = Path(tmpdir) / "post.png"
            pre.write_bytes(b"fake")
            post.write_bytes(b"fake")

            scene = {
                "pre_image_url": "https://example.com/pre.png",
                "post_image_url": "https://example.com/post.png",
                "pre_image_path": str(pre),
                "post_image_path": str(post),
            }
            with mock.patch("src.dashboard.artifact_resolver.PROJECT_ROOT", Path("/")):
                pre_url, post_url, _pre_p, _post_p = scene_image_sources(scene)

            self.assertIsNone(pre_url)
            self.assertIsNone(post_url)

    def test_build_report_csv(self) -> None:
        from src.dashboard.artifact_resolver import build_report_csv

        summary = {"scene_id": "s1", "priority_score": 85.0, "class_counts": {"destroyed": 5}}
        preds = [
            {
                "building_id": "b1",
                "predicted_label": "destroyed",
                "confidence": 0.9,
                "needs_review": False,
            }
        ]
        csv_str = build_report_csv(summary, preds)
        self.assertIn("section,key,value", csv_str)
        self.assertIn("s1", csv_str)
        self.assertIn("destroyed", csv_str)

    def test_resolve_confusion_matrix_image_none(self) -> None:
        from src.dashboard.artifact_resolver import resolve_confusion_matrix_image

        paths = {"figures_dir": Path("/nonexistent")}
        self.assertIsNone(resolve_confusion_matrix_image(paths=paths))


class TestOverlays(unittest.TestCase):
    """Overlay drawing and image helpers."""

    def test_placeholder_image_size(self) -> None:
        from src.dashboard.overlays import _placeholder_image

        img = _placeholder_image(320, 240, "Test")
        self.assertEqual(img.size, (320, 240))

    def test_load_display_image_fallback(self) -> None:
        from src.dashboard.overlays import load_display_image

        img = load_display_image(None, "Pre-disaster")
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.size, (640, 360))

    def test_load_display_image_from_file(self) -> None:
        from src.dashboard.overlays import load_display_image

        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "test.png"
        img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
        img.save(path)
        loaded = load_display_image(path, "Test")
        self.assertEqual(loaded.size, (100, 100))
        loaded.close()
        path.unlink(missing_ok=True)
        os.rmdir(tmpdir)

    def test_draw_demo_overlays_no_predictions(self) -> None:
        from src.dashboard.overlays import draw_demo_overlays

        img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
        result = draw_demo_overlays(img, [])
        self.assertEqual(result.size, img.size)

    def test_draw_demo_overlays_with_predictions(self) -> None:
        from src.dashboard.overlays import draw_demo_overlays

        img = Image.fromarray(np.zeros((200, 200, 3), dtype=np.uint8))
        preds = [
            {"predicted_label": "destroyed", "needs_review": False},
            {"predicted_label": "no_damage", "needs_review": False},
            {"predicted_label": "minor_damage", "needs_review": True},
        ]
        result = draw_demo_overlays(img, preds, opacity=0.5)
        self.assertEqual(result.size, (200, 200))
        self.assertEqual(result.mode, "RGB")
        result_arr = np.array(result)
        self.assertTrue(result_arr.max() > 0)


if __name__ == "__main__":
    unittest.main()
