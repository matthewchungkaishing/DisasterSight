"""Tests for dashboard pure-logic modules.

Tests cover :mod:`labels`, :mod:`priority`, :mod:`map_explorer` table data,
:mod:`artifact_resolver`, and :mod:`overlays` — all the modules that can be
exercised without a running Streamlit server.
"""

from __future__ import annotations

import inspect
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
        from src.common.priority_score import compute_shares

        counts = {"no_damage": 0, "minor_damage": 0, "major_damage": 0, "destroyed": 10}
        shares = compute_shares(counts, 10)
        self.assertAlmostEqual(shares["destroyed_share"], 1.0)
        self.assertAlmostEqual(shares["damage_density"], 1.0)

    def test_compute_shares_zero_total(self) -> None:
        from src.common.priority_score import compute_shares

        shares = compute_shares({}, 0)
        self.assertEqual(shares["destroyed_share"], 0.0)
        self.assertEqual(shares["damage_density"], 0.0)

    def test_compute_shares_mixed(self) -> None:
        from src.common.priority_score import compute_shares

        counts = {"no_damage": 5, "minor_damage": 2, "major_damage": 2, "destroyed": 1}
        shares = compute_shares(counts, 10)
        self.assertAlmostEqual(shares["destroyed_share"], 0.1)
        self.assertAlmostEqual(shares["major_damage_share"], 0.2)
        self.assertAlmostEqual(shares["damage_density"], 0.5)

    def test_compute_priority_score_max(self) -> None:
        from src.common.priority_score import compute_priority_score

        score = compute_priority_score(
            1.0,
            1.0,
            1.0,
            destroyed_weight=0.5,
            major_damage_weight=0.3,
            damage_density_weight=0.2,
        )
        self.assertAlmostEqual(score, 100.0)

    def test_compute_priority_score_zero(self) -> None:
        from src.common.priority_score import compute_priority_score

        score = compute_priority_score(
            0.0,
            0.0,
            0.0,
            destroyed_weight=0.5,
            major_damage_weight=0.3,
            damage_density_weight=0.2,
        )
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


class TestSidebarState(unittest.TestCase):
    """Sidebar session state helpers."""

    def test_init_and_get_sidebar_state(self) -> None:
        import streamlit as st

        from src.dashboard.sidebar_state import (
            SIDEBAR_STATE_KEY,
            get_sidebar_state,
            init_sidebar_state,
        )

        st.session_state.clear()
        init_sidebar_state("collapsed")
        self.assertEqual(st.session_state[SIDEBAR_STATE_KEY], "collapsed")
        self.assertEqual(get_sidebar_state(), "collapsed")

        st.session_state.clear()
        init_sidebar_state("expanded")
        self.assertEqual(get_sidebar_state(), "expanded")


class TestReviewQueue(unittest.TestCase):
    """Review queue pending counts and headings."""

    def _summaries(self) -> list[dict[str, Any]]:
        return [
            {"scene_id": "a", "review_flag_count": 2},
            {"scene_id": "b", "review_flag_count": 0},
            {"scene_id": "c", "review_flag_count": 1},
        ]

    def test_pending_building_count(self) -> None:
        from src.dashboard.components.review_queue import count_pending_buildings

        self.assertEqual(count_pending_buildings(self._summaries()), 3)

    def test_pending_scene_count(self) -> None:
        from src.dashboard.components.review_queue import count_pending_scenes

        self.assertEqual(count_pending_scenes(self._summaries()), 2)

    def test_review_queue_heading_zero(self) -> None:
        from src.dashboard.components.review_queue import review_queue_heading

        self.assertEqual(review_queue_heading([]), "Review Queue")

    def test_review_queue_heading_buildings(self) -> None:
        from src.dashboard.components.review_queue import review_queue_heading

        self.assertEqual(
            review_queue_heading(self._summaries()),
            "Review Queue (3 buildings flagged)",
        )

    def test_review_queue_heading_singular(self) -> None:
        from src.dashboard.components.review_queue import review_queue_heading

        self.assertEqual(
            review_queue_heading([{"review_flag_count": 1}]),
            "Review Queue (1 building flagged)",
        )


class TestMapExplorerTableData(unittest.TestCase):
    """Map Explorer filter, sort, and pagination (pure logic)."""

    def _sample_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "scene_id": "a",
                "priority_score": 10,
                "review_flag_count": 0,
                "destroyed_share": 0.1,
                "split": "train",
            },
            {
                "scene_id": "b",
                "priority_score": 90,
                "review_flag_count": 2,
                "destroyed_share": 0.8,
                "split": "test",
            },
            {
                "scene_id": "c",
                "priority_score": 50,
                "review_flag_count": 1,
                "destroyed_share": 0.5,
                "split": "val",
            },
        ]

    def test_filter_review_required(self) -> None:
        from src.dashboard.components.map_explorer.table_data import filter_and_sort_rows

        rows = filter_and_sort_rows(self._sample_rows(), "Review Required", "Priority Score")
        self.assertEqual([r["scene_id"] for r in rows], ["b", "c"])

    def test_filter_test_split(self) -> None:
        from src.dashboard.components.map_explorer.table_data import filter_and_sort_rows

        rows = filter_and_sort_rows(self._sample_rows(), "Test", "Priority Score")
        self.assertEqual([r["scene_id"] for r in rows], ["b"])

    def test_sort_by_review_count(self) -> None:
        from src.dashboard.components.map_explorer.table_data import filter_and_sort_rows

        rows = filter_and_sort_rows(self._sample_rows(), "All", "Review count")
        self.assertEqual([r["scene_id"] for r in rows], ["b", "c", "a"])

    def test_clamp_page_bounds(self) -> None:
        from src.dashboard.components.map_explorer.table_data import clamp_page, max_page_index

        self.assertEqual(max_page_index(12, page_size=5), 2)
        self.assertEqual(clamp_page(99, 12, page_size=5), 2)
        self.assertEqual(clamp_page(-1, 12, page_size=5), 0)
        self.assertEqual(clamp_page(0, 0, page_size=5), 0)

    def test_paginate_rows_slice(self) -> None:
        from src.dashboard.components.map_explorer.table_data import paginate_rows

        rows = [{"scene_id": str(i)} for i in range(7)]
        page_rows, start, end, clamped = paginate_rows(rows, 1, page_size=3)
        self.assertEqual(start, 3)
        self.assertEqual(end, 6)
        self.assertEqual(clamped, 1)
        self.assertEqual(len(page_rows), 3)
        self.assertEqual(page_rows[0]["scene_id"], "3")


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

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        import csv as csv_mod

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv_mod.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

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

    def test_resolve_scenes_from_scene_manifest_csv(self) -> None:
        from src.dashboard.artifact_resolver import resolve_scenes

        with tempfile.TemporaryDirectory() as tmpdir:
            manifests = Path(tmpdir) / "artifacts" / "manifests"
            fields = [
                "scene_id",
                "disaster_name",
                "disaster_type",
                "pre_image_path",
                "post_image_path",
                "pre_json_path",
                "post_json_path",
                "label_json_path",
                "split",
            ]
            self._write_csv(
                manifests / "scene_manifest.csv",
                fields,
                [
                    {
                        "scene_id": "real-xbd-001",
                        "disaster_name": "real-event",
                        "disaster_type": "earthquake",
                        "pre_image_path": "data/raw/pre.png",
                        "post_image_path": "data/raw/post.png",
                        "pre_json_path": "data/raw/pre.json",
                        "post_json_path": "data/raw/post.json",
                        "label_json_path": "data/raw/post.json",
                        "split": "test",
                    }
                ],
            )

            records, is_fixture = resolve_scenes(
                paths={"processed_data_dir": Path("/nonexistent"), "manifests_dir": manifests}
            )

            self.assertFalse(is_fixture)
            self.assertEqual(records[0]["scene_id"], "real-xbd-001")

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
            result, is_fixture = resolve_predictions("s1", paths=paths)
            self.assertFalse(is_fixture)
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
            result, is_fixture = resolve_predictions("s1", paths=paths)
            self.assertFalse(is_fixture)
            self.assertEqual(len(result), 2)

    def test_resolve_metrics_fixture_fallback(self) -> None:
        from src.dashboard.artifact_resolver import resolve_metrics

        paths = {"artifacts_dir": Path("/nonexistent"), "figures_dir": Path("/nonexistent")}
        metrics, is_fixture = resolve_metrics(paths=paths)
        self.assertTrue(is_fixture)
        self.assertIn("macro_f1", metrics)

    def test_resolve_zone_summaries_fixture_fallback(self) -> None:
        from src.dashboard.artifact_resolver import resolve_zone_summaries

        paths = {"artifacts_dir": Path("/nonexistent"), "processed_data_dir": Path("/nonexistent")}
        paths["predictions_dir"] = Path("/nonexistent")
        records, is_fixture = resolve_zone_summaries(paths=paths)
        self.assertTrue(is_fixture)
        self.assertGreater(len(records), 0)
        scores = [r.get("priority_score", 0) for r in records]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_resolve_image_path_missing(self) -> None:
        from src.dashboard.artifact_resolver import resolve_image_path

        self.assertIsNone(resolve_image_path(""))
        self.assertIsNone(resolve_image_path("data/nonexistent/image.png"))

    def test_scene_local_image_paths(self) -> None:
        from src.dashboard.artifact_resolver import scene_has_local_images, scene_local_image_paths

        with tempfile.TemporaryDirectory() as tmpdir:
            pre = Path(tmpdir) / "pre.png"
            post = Path(tmpdir) / "post.png"
            pre.write_bytes(b"fake")
            post.write_bytes(b"fake")

            scene = {
                "pre_image_path": str(pre),
                "post_image_path": str(post),
            }
            with mock.patch("src.dashboard.artifact_resolver.PROJECT_ROOT", Path("/")):
                pre_path, post_path = scene_local_image_paths(scene)

            self.assertIsNotNone(pre_path)
            self.assertIsNotNone(post_path)
            self.assertTrue(scene_has_local_images(scene))

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

    def test_prioritize_scene_ids_prefers_predictions_and_images(self) -> None:
        from src.dashboard.artifact_resolver import prioritize_scene_ids

        scenes = [
            {"scene_id": "scene-a", "pre_image_path": "", "post_image_path": ""},
            {"scene_id": "scene-b", "pre_image_path": "", "post_image_path": ""},
        ]
        summaries = [
            {"scene_id": "scene-a", "priority_score": 99.0},
            {"scene_id": "scene-b", "priority_score": 50.0},
        ]
        ordered = prioritize_scene_ids(scenes, summaries, {"scene-b"})
        self.assertEqual(ordered[0], "scene-b")

    def test_resolve_prediction_scene_ids_from_csv(self) -> None:
        from src.dashboard.artifact_resolver import resolve_prediction_scene_ids

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            pred_dir.mkdir(parents=True)
            csv_path = pred_dir / "building_predictions_test.csv"
            csv_path.write_text(
                "scene_id,building_id\nscene-x,b1\nscene-y,b2\n",
                encoding="utf-8",
            )
            scene_ids = resolve_prediction_scene_ids(paths={"predictions_dir": pred_dir})
            self.assertEqual(scene_ids, {"scene-x", "scene-y"})


class TestArtifactResolverCSV(unittest.TestCase):
    """CSV artifact resolution — inference pipeline outputs."""

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        import csv as csv_mod

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv_mod.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_resolve_predictions_from_building_csv(self) -> None:
        from src.dashboard.artifact_resolver import resolve_predictions

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            fields = [
                "scene_id",
                "building_id",
                "disaster_name",
                "disaster_type",
                "split",
                "true_label",
                "predicted_label",
                "confidence",
                "needs_review",
                "class_probabilities",
                "polygon_xy",
                "bbox_x1",
                "bbox_y1",
                "bbox_x2",
                "bbox_y2",
                "pre_crop_path",
                "post_crop_path",
            ]
            p_a = '{"no_damage":0.02,"minor_damage":0.03,"major_damage":0.03,"destroyed":0.92}'
            p_b = '{"no_damage":0.88,"minor_damage":0.08,"major_damage":0.03,"destroyed":0.01}'
            rows = [
                {
                    "scene_id": "scene-A",
                    "building_id": "b1",
                    "disaster_name": "test-event",
                    "disaster_type": "earthquake",
                    "split": "test",
                    "true_label": "destroyed",
                    "predicted_label": "destroyed",
                    "confidence": "0.92",
                    "needs_review": "False",
                    "class_probabilities": p_a,
                    "polygon_xy": "[]",
                    "bbox_x1": "10",
                    "bbox_y1": "20",
                    "bbox_x2": "50",
                    "bbox_y2": "60",
                    "pre_crop_path": "crops/a_pre.png",
                    "post_crop_path": "crops/a_post.png",
                },
                {
                    "scene_id": "scene-B",
                    "building_id": "b2",
                    "disaster_name": "other",
                    "disaster_type": "flood",
                    "split": "test",
                    "true_label": "no_damage",
                    "predicted_label": "no_damage",
                    "confidence": "0.88",
                    "needs_review": "False",
                    "class_probabilities": p_b,
                    "polygon_xy": "[]",
                    "bbox_x1": "0",
                    "bbox_y1": "0",
                    "bbox_x2": "30",
                    "bbox_y2": "30",
                    "pre_crop_path": "",
                    "post_crop_path": "",
                },
            ]
            self._write_csv(pred_dir / "building_predictions_test.csv", fields, rows)
            paths = {"predictions_dir": pred_dir}

            result, is_fixture = resolve_predictions("scene-A", paths=paths)
            self.assertFalse(is_fixture)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["building_id"], "b1")
            self.assertAlmostEqual(result[0]["confidence"], 0.92)
            self.assertFalse(result[0]["needs_review"])
            self.assertEqual(result[0]["bbox_x2"], 50)
            self.assertIsInstance(result[0]["class_probabilities"], dict)

    def test_resolve_predictions_csv_type_coercion(self) -> None:
        from src.dashboard.artifact_resolver import resolve_predictions

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            fields = [
                "scene_id",
                "building_id",
                "disaster_name",
                "disaster_type",
                "split",
                "true_label",
                "predicted_label",
                "confidence",
                "needs_review",
                "class_probabilities",
                "polygon_xy",
                "bbox_x1",
                "bbox_y1",
                "bbox_x2",
                "bbox_y2",
                "pre_crop_path",
                "post_crop_path",
            ]
            rows = [
                {
                    "scene_id": "s1",
                    "building_id": "b1",
                    "disaster_name": "e",
                    "disaster_type": "wildfire",
                    "split": "test",
                    "true_label": "minor_damage",
                    "predicted_label": "minor_damage",
                    "confidence": "0.55",
                    "needs_review": "True",
                    "class_probabilities": "{}",
                    "polygon_xy": "[]",
                    "bbox_x1": "5",
                    "bbox_y1": "5",
                    "bbox_x2": "15",
                    "bbox_y2": "15",
                    "pre_crop_path": "",
                    "post_crop_path": "",
                }
            ]
            self._write_csv(pred_dir / "building_predictions_test.csv", fields, rows)
            paths = {"predictions_dir": pred_dir}

            result, is_fixture = resolve_predictions("s1", paths=paths)
            self.assertFalse(is_fixture)
            self.assertTrue(result[0]["needs_review"])
            self.assertEqual(result[0]["bbox_x1"], 5)

    def test_resolve_zone_summaries_from_scene_summary_csv(self) -> None:
        from src.dashboard.artifact_resolver import resolve_zone_summaries

        with tempfile.TemporaryDirectory() as tmpdir:
            pred_dir = Path(tmpdir) / "predictions"
            fields = [
                "scene_id",
                "disaster_name",
                "disaster_type",
                "split",
                "total_buildings",
                "class_counts",
                "destroyed_share",
                "major_damage_share",
                "damage_density",
                "priority_score",
                "review_flag_count",
                "mean_confidence",
            ]
            cc_s1 = '{"no_damage":2,"minor_damage":2,"major_damage":2,"destroyed":4}'
            cc_s2 = '{"no_damage":4,"minor_damage":1,"major_damage":0,"destroyed":0}'
            rows = [
                {
                    "scene_id": "s1",
                    "disaster_name": "event-A",
                    "disaster_type": "earthquake",
                    "split": "test",
                    "total_buildings": "10",
                    "class_counts": cc_s1,
                    "destroyed_share": "0.4",
                    "major_damage_share": "0.2",
                    "damage_density": "0.8",
                    "priority_score": "46.0",
                    "review_flag_count": "2",
                    "mean_confidence": "0.75",
                },
                {
                    "scene_id": "s2",
                    "disaster_name": "event-B",
                    "disaster_type": "flood",
                    "split": "test",
                    "total_buildings": "5",
                    "class_counts": cc_s2,
                    "destroyed_share": "0.0",
                    "major_damage_share": "0.0",
                    "damage_density": "0.2",
                    "priority_score": "4.0",
                    "review_flag_count": "0",
                    "mean_confidence": "0.88",
                },
            ]
            self._write_csv(pred_dir / "scene_summaries_test.csv", fields, rows)
            paths = {
                "predictions_dir": pred_dir,
                "artifacts_dir": Path("/nonexistent"),
                "processed_data_dir": Path("/nonexistent"),
            }

            records, is_fixture = resolve_zone_summaries(paths=paths)
            self.assertFalse(is_fixture)
            self.assertEqual(len(records), 2)
            # Sorted by priority descending
            self.assertEqual(records[0]["scene_id"], "s1")
            self.assertAlmostEqual(records[0]["priority_score"], 46.0)
            self.assertIsInstance(records[0]["class_counts"], dict)
            self.assertEqual(records[0]["total_buildings"], 10)

    def test_normalize_eval_metrics_from_eval_results_json(self) -> None:
        from src.common.metrics_format import format_dashboard_metrics

        raw = {
            "split": "test",
            "num_samples": 1000,
            "macro_f1": 0.812,
            "precision_macro": 0.835,
            "recall_macro": 0.798,
            "mean_confidence": 0.71,
            "low_confidence_count": 42,
            "per_class_f1": {
                "no_damage": 0.9,
                "minor_damage": 0.7,
                "major_damage": 0.8,
                "destroyed": 0.85,
            },
            "confusion_matrix": {
                "classes": ["no_damage", "minor_damage", "major_damage", "destroyed"],
                "matrix": [
                    [90, 5, 3, 2],
                    [4, 70, 15, 11],
                    [3, 12, 75, 10],
                    [2, 4, 8, 86],
                ],
            },
        }
        result = format_dashboard_metrics(raw)
        self.assertIn("macro_f1", result)
        self.assertAlmostEqual(result["macro_f1"], 0.812)
        self.assertAlmostEqual(result["precision_macro"], 0.835)
        self.assertEqual(result["validation_patches"], 1000)
        self.assertEqual(len(result["confusion_matrix"]), 4)
        # Row sums of normalized matrix should be ~1.0
        for row in result["confusion_matrix"]:
            self.assertAlmostEqual(sum(row), 1.0, places=2)

    def test_resolve_metrics_from_eval_results_json(self) -> None:
        from src.dashboard.artifact_resolver import resolve_metrics

        with tempfile.TemporaryDirectory() as tmpdir:
            figures = Path(tmpdir) / "figures"
            figures.mkdir()
            eval_data = {
                "split": "test",
                "num_samples": 500,
                "macro_f1": 0.75,
                "precision_macro": 0.78,
                "recall_macro": 0.72,
                "mean_confidence": 0.68,
                "low_confidence_count": 30,
                "per_class_f1": {},
                "confusion_matrix": {
                    "classes": ["no_damage", "minor_damage", "major_damage", "destroyed"],
                    "matrix": [[10, 0, 0, 0], [0, 10, 0, 0], [0, 0, 10, 0], [0, 0, 0, 10]],
                },
            }
            (figures / "eval_results_test.json").write_text(json.dumps(eval_data), encoding="utf-8")
            paths = {
                "artifacts_dir": Path("/nonexistent"),
                "figures_dir": figures,
            }
            result, is_fixture = resolve_metrics(paths=paths)
            self.assertFalse(is_fixture)
            self.assertAlmostEqual(result["macro_f1"], 0.75)
            self.assertIn("confusion_matrix", result)

    def test_resolve_confusion_matrix_image_split_named(self) -> None:
        from src.dashboard.artifact_resolver import resolve_confusion_matrix_image

        with tempfile.TemporaryDirectory() as tmpdir:
            figures = Path(tmpdir) / "figures"
            figures.mkdir()
            img_path = figures / "confusion_matrix_test.png"
            img_path.write_bytes(b"fake png")
            paths = {"figures_dir": figures}
            result = resolve_confusion_matrix_image(paths=paths)
            self.assertIsNotNone(result)
            self.assertEqual(result, img_path)


class TestDashboardCaching(unittest.TestCase):
    """Streamlit cache invalidation helpers."""

    def test_cached_loader_tokens_are_hashed_by_streamlit(self) -> None:
        from src.dashboard import data_loaders

        cached_functions = [
            data_loaders._load_scenes_cached,
            data_loaders._load_zone_summaries_cached,
            data_loaders._load_predictions_cached,
            data_loaders._load_metrics_cached,
        ]

        for func in cached_functions:
            params = inspect.signature(func).parameters
            self.assertIn("token", params)
            self.assertNotIn("_token", params)

    def test_artifact_token_changes_when_prediction_artifact_appears(self) -> None:
        from src.dashboard import data_loaders

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path_map = {
                "manifests_dir": root / "manifests",
                "predictions_dir": root / "predictions",
                "figures_dir": root / "figures",
                "artifacts_dir": root / "artifacts",
                "processed_data_dir": root / "processed",
            }
            for path in path_map.values():
                path.mkdir(parents=True, exist_ok=True)

            with mock.patch("src.dashboard.data_loaders.get_path_map", return_value=path_map):
                before = data_loaders._artifact_token("predictions", "scene-1")
                (path_map["predictions_dir"] / "building_predictions_test.csv").write_text(
                    "scene_id,building_id,predicted_label\nscene-1,b1,destroyed\n",
                    encoding="utf-8",
                )
                after = data_loaders._artifact_token("predictions", "scene-1")

        self.assertNotEqual(before, after)


class TestSceneViewerLayout(unittest.TestCase):
    """Pure layout sizing for the scene explorer."""

    def test_square_image_fills_slot_by_default(self) -> None:
        from src.dashboard.components.scene_viewer_layout import compute_scene_viewer_layout

        layout = compute_scene_viewer_layout(
            1024,
            1024,
            estimated_container_width_px=960,
        )
        self.assertEqual(layout.pane_display_height_px, 480)
        self.assertEqual(layout.pane_display_width_px, 480)
        self.assertEqual(layout.pane_slot_width_px, 480)
        self.assertEqual(layout.component_height_px, 480 + 44)

    def test_square_image_caps_at_explicit_max_height(self) -> None:
        from src.dashboard.components.scene_viewer_layout import compute_scene_viewer_layout

        layout = compute_scene_viewer_layout(
            1024,
            1024,
            max_pane_height_px=420,
            estimated_container_width_px=960,
        )
        self.assertEqual(layout.pane_display_height_px, 420)
        self.assertEqual(layout.pane_display_width_px, 420)
        self.assertEqual(layout.pane_slot_width_px, 480)
        self.assertEqual(layout.component_height_px, 420 + 44)

    def test_portrait_image_centers_with_narrower_pane(self) -> None:
        from src.dashboard.components.scene_viewer_layout import compute_scene_viewer_layout

        layout = compute_scene_viewer_layout(
            800,
            1200,
            max_pane_height_px=420,
            estimated_container_width_px=960,
        )
        self.assertEqual(layout.pane_display_height_px, 420)
        self.assertEqual(layout.pane_display_width_px, 280)

    def test_wide_image_scales_by_width_before_cap(self) -> None:
        from src.dashboard.components.scene_viewer_layout import (
            compute_pane_display_height,
            compute_pane_display_size,
        )

        height = compute_pane_display_height(
            2048,
            1024,
            pane_width_px=480,
            max_pane_height_px=420,
        )
        self.assertEqual(height, 240)
        width, sized_height = compute_pane_display_size(
            2048,
            1024,
            pane_slot_width_px=480,
            max_pane_height_px=420,
        )
        self.assertEqual((width, sized_height), (480, 240))

    def test_layout_config_defaults_from_yaml(self) -> None:
        from src.dashboard.config import get_scene_viewer_layout_settings

        settings = get_scene_viewer_layout_settings()
        self.assertNotIn("max_pane_height_px", settings)
        self.assertEqual(settings["estimated_container_width_px"], 1120)
        self.assertEqual(settings["grid_padding_px"], 0)


class TestMetricQuadrant(unittest.TestCase):
    """Scene KPI quadrant HTML contract."""

    def test_quadrant_has_four_ordered_cells(self) -> None:
        from src.dashboard.components.metrics import build_quadrant_html, build_scene_metric_cells

        cells = build_scene_metric_cells(159, 26.0, 158, {"minor_damage": 120, "major_damage": 30})
        html_output = build_quadrant_html(cells)

        self.assertIn('class="ds-metrics-quadrant"', html_output)
        self.assertEqual(html_output.count("ds-metrics-quadrant__cell"), 4)
        self.assertIn('data-metric="total_buildings"', html_output)
        self.assertIn('data-metric="priority_score"', html_output)
        self.assertIn('data-metric="review_count"', html_output)
        self.assertIn('data-metric="dominant_class"', html_output)
        self.assertNotIn("ds-metrics-stack", html_output)

    def test_quadrant_cell_order(self) -> None:
        from src.dashboard.components.metrics import build_quadrant_html, build_scene_metric_cells

        cells = build_scene_metric_cells(1, 2.0, 3, {"destroyed": 1})
        html_output = build_quadrant_html(cells)
        total_idx = html_output.index("total_buildings")
        priority_idx = html_output.index("priority_score")
        review_idx = html_output.index("review_count")
        dominant_idx = html_output.index("dominant_class")
        self.assertLess(total_idx, priority_idx)
        self.assertLess(priority_idx, review_idx)
        self.assertLess(review_idx, dominant_idx)


class TestImageViewer(unittest.TestCase):
    """Interactive image viewer HTML contract."""

    def test_viewer_html_contract(self) -> None:
        from pathlib import Path

        from src.dashboard.components.scene_viewer import (
            CARD_BACKGROUND,
            ImagePane,
            build_scene_viewer_html,
        )
        from src.dashboard.components.scene_viewer_layout import compute_scene_viewer_layout

        layout = compute_scene_viewer_layout(1024, 1024, max_pane_height_px=420)
        html_output = build_scene_viewer_html(
            "Scene Explorer - Wildfire",
            "Mean confidence: 82%",
            (
                ImagePane(
                    "pre",
                    "Pre-disaster",
                    "data:image/jpeg;base64,aaa",
                    "Pre image",
                    width=1024,
                    height=1024,
                ),
                ImagePane(
                    "post",
                    "Post-disaster",
                    "data:image/jpeg;base64,bbb",
                    "Post image",
                    width=1024,
                    height=1024,
                ),
            ),
            layout,
        )

        self.assertEqual(CARD_BACKGROUND, "#2A3348")
        self.assertIn("scene-viewer__grid", html_output)
        self.assertIn("gap: 0", html_output)
        self.assertIn("padding: 0", html_output)
        self.assertIn("pane-slot", html_output)
        self.assertIn("pane-viewport", html_output)
        self.assertIn("pane-layer", html_output)
        self.assertIn("--pane-max-height: 420px", html_output)
        self.assertIn("background: var(--card-bg)", html_output)
        self.assertIn("open_in_full", html_output)
        self.assertIn("close_fullscreen", html_output)
        self.assertIn('data-mode-action="solo"', html_output)
        self.assertIn('data-mode-action="split"', html_output)
        self.assertIn("class PaneViewport", html_output)
        self.assertNotIn("lightbox", html_output)
        self.assertIn("object-fit: contain", html_output)
        self.assertNotIn('target="_blank"', html_output)

        viewer_js = Path("src/dashboard/components/scene_viewer/assets/viewer.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("class PaneViewport", viewer_js)

    def test_global_theme_uses_requested_background(self) -> None:
        theme_css = Path("src/dashboard/theme.css").read_text(encoding="utf-8")

        self.assertIn("--ds-app-background: #765FEF", theme_css)
        self.assertIn("background: var(--ds-app-background) !important", theme_css)
        self.assertNotIn("linear-gradient(135deg, #28374f", theme_css)


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

    def test_draw_prediction_overlays_skips_without_bbox(self) -> None:
        from src.dashboard.overlays import draw_prediction_overlays

        img = Image.fromarray(np.zeros((200, 200, 3), dtype=np.uint8))
        preds = [{"predicted_label": "no_damage", "needs_review": False}]
        result = draw_prediction_overlays(img, preds)
        self.assertEqual(result.size, (200, 200))
        self.assertTrue(np.array_equal(np.array(result), np.array(img)))

    def test_has_valid_bboxes_with_valid_coords(self) -> None:
        from src.dashboard.overlays import _has_valid_bboxes

        preds = [{"bbox_x1": 10, "bbox_y1": 20, "bbox_x2": 50, "bbox_y2": 60}]
        self.assertTrue(_has_valid_bboxes(preds))

    def test_has_valid_bboxes_with_zero_coords(self) -> None:
        from src.dashboard.overlays import _has_valid_bboxes

        preds = [{"bbox_x1": 0, "bbox_y1": 0, "bbox_x2": 0, "bbox_y2": 0}]
        self.assertFalse(_has_valid_bboxes(preds))

    def test_has_valid_bboxes_empty(self) -> None:
        from src.dashboard.overlays import _has_valid_bboxes

        self.assertFalse(_has_valid_bboxes([]))

    def test_draw_bbox_overlays_with_valid_bbox(self) -> None:
        from src.dashboard.overlays import draw_bbox_overlays

        img = Image.fromarray(np.zeros((200, 200, 3), dtype=np.uint8))
        preds = [
            {
                "predicted_label": "destroyed",
                "needs_review": False,
                "bbox_x1": 10,
                "bbox_y1": 10,
                "bbox_x2": 50,
                "bbox_y2": 50,
            }
        ]
        result = draw_bbox_overlays(img, preds, opacity=0.5)
        self.assertEqual(result.size, (200, 200))
        self.assertEqual(result.mode, "RGB")
        result_arr = np.array(result)
        # Pixels inside the bbox region should be non-zero
        self.assertTrue(result_arr[20:40, 20:40].max() > 0)

    def test_draw_bbox_overlays_clamps_out_of_bounds(self) -> None:
        from src.dashboard.overlays import draw_bbox_overlays

        img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
        preds = [
            {
                "predicted_label": "major_damage",
                "needs_review": False,
                "bbox_x1": -5,
                "bbox_y1": -5,
                "bbox_x2": 200,
                "bbox_y2": 200,
            }
        ]
        # Should not raise; out-of-bounds coords are clamped to image size
        result = draw_bbox_overlays(img, preds)
        self.assertEqual(result.size, (100, 100))

    def test_draw_prediction_overlays_uses_bbox_when_available(self) -> None:
        from src.dashboard.overlays import draw_prediction_overlays

        img = Image.fromarray(np.zeros((200, 200, 3), dtype=np.uint8))
        preds = [
            {
                "predicted_label": "destroyed",
                "needs_review": False,
                "bbox_x1": 40,
                "bbox_y1": 40,
                "bbox_x2": 80,
                "bbox_y2": 80,
            }
        ]
        result = draw_prediction_overlays(img, preds)
        self.assertEqual(result.size, (200, 200))
        result_arr = np.array(result)
        self.assertTrue(result_arr.max() > 0)


class TestDataLoadersSceneSelection(unittest.TestCase):
    """Scene ID resolution for dashboard sidebar/content alignment."""

    def test_resolve_selected_scene_id_prefers_scene_with_predictions(self) -> None:
        from src.dashboard import data_loaders

        with (
            mock.patch.object(data_loaders, "load_scene_ids", return_value=["scene-a", "scene-b"]),
            mock.patch.object(
                data_loaders,
                "load_predictions",
                side_effect=lambda sid: [{"building_id": "b1"}] if sid == "scene-b" else [],
            ),
        ):
            self.assertEqual(
                data_loaders.resolve_selected_scene_id("scene-a"),
                "scene-b",
            )

    def test_resolve_selected_scene_id_keeps_preferred_when_it_has_predictions(self) -> None:
        from src.dashboard import data_loaders

        with (
            mock.patch.object(data_loaders, "load_scene_ids", return_value=["scene-a", "scene-b"]),
            mock.patch.object(
                data_loaders,
                "load_predictions",
                side_effect=lambda sid: [{"building_id": "b1"}] if sid == "scene-a" else [],
            ),
        ):
            self.assertEqual(
                data_loaders.resolve_selected_scene_id("scene-a"),
                "scene-a",
            )


class TestConfusionMatrixDisplay(unittest.TestCase):
    """Confusion matrix rendering prefers loaded metrics over stale PNGs."""

    def test_render_prefers_matrix_over_saved_png(self) -> None:
        source = Path("src/dashboard/components/confusion_matrix.py").read_text(encoding="utf-8")
        render_body = source.split("def render(", maxsplit=1)[1]
        matrix_branch = render_body.index("if not matrix:")
        png_lookup = render_body.index("resolve_confusion_matrix_image")
        self.assertLess(
            matrix_branch,
            png_lookup,
            "render() should only fall back to PNG when matrix is missing",
        )


class TestDemoPredictionFixtures(unittest.TestCase):
    """Demo prediction fixtures support overlay rendering."""

    def test_demo_predictions_include_bbox_fields(self) -> None:
        from src.dashboard.artifact_resolver import resolve_predictions

        with mock.patch(
            "src.dashboard.artifact_resolver._first_existing",
            return_value=None,
        ):
            records, is_fixture = resolve_predictions("pinery-bushfire_00000000")
        self.assertTrue(is_fixture)
        self.assertTrue(records)
        for record in records:
            self.assertIn("bbox_x1", record)
            self.assertIn("bbox_y2", record)


if __name__ == "__main__":
    unittest.main()
