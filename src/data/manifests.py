from __future__ import annotations

import csv
import random
from collections.abc import Iterable
from pathlib import Path

from src.data.xbd import (
    POST_IMAGE_KEY,
    POST_JSON_KEY,
    PRE_IMAGE_KEY,
    PRE_JSON_KEY,
    extract_disaster_name,
    infer_disaster_type,
    is_complete_scene,
)

SCENE_MANIFEST_FIELDS = (
    "scene_id",
    "disaster_name",
    "disaster_type",
    "pre_image_path",
    "post_image_path",
    "pre_json_path",
    "post_json_path",
    "label_json_path",
    "split",
)


def build_scene_manifest_rows(
    scenes: dict[str, dict[str, object]],
    splits: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    split_map = splits or {}

    for scene_id in sorted(scenes):
        record = scenes[scene_id]
        if not is_complete_scene(record):
            continue

        disaster_name = str(record.get("disaster_name") or extract_disaster_name(scene_id))
        disaster_type = str(record.get("disaster_type") or infer_disaster_type(scene_id))
        post_json_path = str(record[POST_JSON_KEY])
        rows.append(
            {
                "scene_id": scene_id,
                "disaster_name": disaster_name,
                "disaster_type": disaster_type,
                "pre_image_path": str(record[PRE_IMAGE_KEY]),
                "post_image_path": str(record[POST_IMAGE_KEY]),
                "pre_json_path": str(record[PRE_JSON_KEY]),
                "post_json_path": post_json_path,
                "label_json_path": post_json_path,
                "split": split_map.get(scene_id, ""),
            }
        )

    return rows


def make_event_aware_splits(
    scene_ids: Iterable[str],
    train_fraction: float,
    val_fraction: float,
    test_fraction: float,
    seed: int,
) -> dict[str, str]:
    total_fraction = train_fraction + val_fraction + test_fraction
    if not 0.99 <= total_fraction <= 1.01:
        raise ValueError("train/val/test fractions must sum to 1.0.")

    scene_ids_by_event: dict[str, list[str]] = {}
    for scene_id in scene_ids:
        scene_ids_by_event.setdefault(extract_disaster_name(scene_id), []).append(scene_id)

    events = sorted(scene_ids_by_event)
    rng = random.Random(seed)
    rng.shuffle(events)

    total_scenes = sum(len(scene_ids_by_event[event]) for event in events)
    train_target = total_scenes * train_fraction
    val_target = total_scenes * val_fraction

    split_by_scene: dict[str, str] = {}
    assigned_train = 0
    assigned_val = 0

    for event in events:
        event_scene_ids = sorted(scene_ids_by_event[event])
        if assigned_train < train_target:
            split = "train"
            assigned_train += len(event_scene_ids)
        elif assigned_val < val_target:
            split = "val"
            assigned_val += len(event_scene_ids)
        else:
            split = "test"

        for scene_id in event_scene_ids:
            split_by_scene[scene_id] = split

    return split_by_scene


def write_scene_manifest_csv(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCENE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
