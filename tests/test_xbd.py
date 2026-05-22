from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.data.manifests import build_scene_manifest_rows, make_event_aware_splits
from src.data.xbd import (
    POST_IMAGE_KEY,
    POST_JSON_KEY,
    PRE_IMAGE_KEY,
    PRE_JSON_KEY,
    classify_file_role,
    compute_bbox,
    extract_building_annotations,
    extract_disaster_name,
    extract_scene_id,
    infer_disaster_type,
    is_complete_scene,
    normalise_label,
    polygon_points_from_wkt,
    scan_xbd_files,
)


class XbdParsingTests(unittest.TestCase):
    def test_file_role_and_scene_id_parsing(self) -> None:
        path = Path("santa-rosa-wildfire_00000315_post_disaster.json")

        self.assertEqual(extract_scene_id(path), "santa-rosa-wildfire_00000315")
        self.assertEqual(classify_file_role(path), POST_JSON_KEY)
        self.assertEqual(
            classify_file_role(Path("santa-rosa-wildfire_00000315_pre_disaster.png")),
            PRE_IMAGE_KEY,
        )

    def test_label_normalisation_uses_canonical_config_names(self) -> None:
        cases = {
            "no-damage": "no_damage",
            "No Damage": "no_damage",
            "minor_damage": "minor_damage",
            "major-damage": "major_damage",
            "destroyed": "destroyed",
            "un-classified": "unclassified",
            None: "unknown",
        }

        for raw_label, expected in cases.items():
            with self.subTest(raw_label=raw_label):
                self.assertEqual(normalise_label(raw_label), expected)

    def test_polygon_wkt_and_bbox_parsing(self) -> None:
        points = polygon_points_from_wkt("POLYGON ((1 2, 5 2, 5 8, 1 8, 1 2))")

        self.assertEqual(points, [(1.0, 2.0), (5.0, 2.0), (5.0, 8.0), (1.0, 8.0)])
        self.assertEqual(compute_bbox(points), (1, 2, 5, 8))

    def test_extract_building_annotations_from_xbd_style_features(self) -> None:
        annotation_data = {
            "features": {
                "xy": [
                    {
                        "wkt": "POLYGON ((1 2, 5 2, 5 8, 1 8, 1 2))",
                        "properties": {
                            "uid": "building-a",
                            "feature_type": "building",
                            "subtype": "major-damage",
                        },
                    },
                    {
                        "wkt": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
                        "properties": {"feature_type": "road", "subtype": "no-damage"},
                    },
                ]
            }
        }

        annotations = extract_building_annotations(annotation_data)

        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0].building_id, "building-a")
        self.assertEqual(annotations[0].label, "major_damage")
        self.assertEqual(annotations[0].bbox_xyxy, (1, 2, 5, 8))
        self.assertEqual(annotations[0].area_pixels, 24)

    def test_scan_xbd_files_builds_complete_scene_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in (
                "pinery-bushfire_00000001_pre_disaster.png",
                "pinery-bushfire_00000001_post_disaster.png",
                "pinery-bushfire_00000001_pre_disaster.json",
                "pinery-bushfire_00000001_post_disaster.json",
            ):
                (root / name).touch()

            scenes = scan_xbd_files(root, keywords=("pinery",))
            record = scenes["pinery-bushfire_00000001"]

        self.assertTrue(is_complete_scene(record))
        self.assertEqual(record["disaster_name"], "pinery-bushfire")
        self.assertEqual(record["disaster_type"], "wildfire")
        self.assertTrue(record[PRE_JSON_KEY].endswith("_pre_disaster.json"))
        self.assertTrue(record[POST_IMAGE_KEY].endswith("_post_disaster.png"))


class ManifestTests(unittest.TestCase):
    def test_disaster_name_and_type_helpers(self) -> None:
        self.assertEqual(extract_disaster_name("mexico-earthquake_00000001"), "mexico-earthquake")
        self.assertEqual(infer_disaster_type("mexico-earthquake_00000001"), "earthquake")

    def test_event_aware_splits_keep_events_together(self) -> None:
        scene_ids = [
            "event-a_00000001",
            "event-a_00000002",
            "event-b_00000001",
            "event-b_00000002",
            "event-c_00000001",
            "event-c_00000002",
        ]

        splits = make_event_aware_splits(
            scene_ids,
            train_fraction=0.5,
            val_fraction=0.25,
            test_fraction=0.25,
            seed=7,
        )

        for event_name in ("event-a", "event-b", "event-c"):
            event_splits = {
                split for scene_id, split in splits.items() if scene_id.startswith(event_name)
            }
            self.assertEqual(len(event_splits), 1)

    def test_scene_manifest_rows_use_contract_field_names(self) -> None:
        scenes = {
            "pinery-bushfire_00000001": {
                "scene_id": "pinery-bushfire_00000001",
                "disaster_name": "pinery-bushfire",
                "disaster_type": "wildfire",
                PRE_IMAGE_KEY: "pre.png",
                POST_IMAGE_KEY: "post.png",
                PRE_JSON_KEY: "pre.json",
                POST_JSON_KEY: "post.json",
            }
        }

        rows = build_scene_manifest_rows(scenes, splits={"pinery-bushfire_00000001": "train"})

        self.assertEqual(rows[0]["pre_image_path"], "pre.png")
        self.assertEqual(rows[0]["post_image_path"], "post.png")
        self.assertEqual(rows[0]["label_json_path"], "post.json")
        self.assertEqual(rows[0]["split"], "train")


if __name__ == "__main__":
    unittest.main()
