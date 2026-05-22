from __future__ import annotations

import csv
import random
from collections.abc import Iterable
from pathlib import Path
from typing import Any

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
    scenes: dict[str, dict[str, Any]],
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


def build_event_aware_scene_manifest_rows(
    scenes: dict[str, dict[str, Any]],
    *,
    train_fraction: float,
    val_fraction: float,
    test_fraction: float,
    seed: int,
) -> list[dict[str, str]]:
    """Build manifest rows and assign splits using complete scenes only."""
    complete_scene_ids = [
        scene_id for scene_id in sorted(scenes) if is_complete_scene(scenes[scene_id])
    ]
    splits = make_event_aware_splits(
        complete_scene_ids,
        train_fraction=train_fraction,
        val_fraction=val_fraction,
        test_fraction=test_fraction,
        seed=seed,
    )
    return build_scene_manifest_rows(scenes, splits=splits)


def select_scene_subset(
    scenes: dict[str, dict[str, Any]],
    *,
    disaster_names: Iterable[str] | None = None,
    disaster_types: Iterable[str] | None = None,
    max_scenes: int | None = None,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """Filter complete scene records while keeping disaster events whole."""
    if max_scenes is not None and max_scenes <= 0:
        raise ValueError("max_scenes must be positive when provided.")

    allowed_names = _normalise_filter_values(disaster_names)
    allowed_types = _normalise_filter_values(disaster_types)
    complete_scenes = {
        scene_id: record
        for scene_id, record in scenes.items()
        if is_complete_scene(record)
        and _record_matches_filters(record, allowed_names, allowed_types, scene_id)
    }

    if max_scenes is None or len(complete_scenes) <= max_scenes:
        return dict(sorted(complete_scenes.items()))

    scene_ids_by_event: dict[str, list[str]] = {}
    for scene_id, record in complete_scenes.items():
        event_name = str(record.get("disaster_name") or extract_disaster_name(scene_id))
        scene_ids_by_event.setdefault(event_name, []).append(scene_id)

    events = sorted(scene_ids_by_event)
    rng = random.Random(seed)
    rng.shuffle(events)

    selected_scene_ids: list[str] = []
    skipped_large_events: list[str] = []
    for event in events:
        event_scene_ids = sorted(scene_ids_by_event[event])
        if len(event_scene_ids) > max_scenes:
            skipped_large_events.append(event)
            continue

        if len(selected_scene_ids) + len(event_scene_ids) <= max_scenes:
            selected_scene_ids.extend(event_scene_ids)

    if not selected_scene_ids and skipped_large_events:
        smallest_large_event = min(
            skipped_large_events,
            key=lambda event: len(scene_ids_by_event[event]),
        )
        selected_scene_ids.extend(sorted(scene_ids_by_event[smallest_large_event]))

    return {scene_id: complete_scenes[scene_id] for scene_id in sorted(selected_scene_ids)}


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

    for event_index, event in enumerate(events):
        event_scene_ids = sorted(scene_ids_by_event[event])
        remaining_events_after_this = len(events) - event_index - 1

        if len(events) >= 3 and remaining_events_after_this == 0:
            split = "test"
        elif len(events) >= 3 and remaining_events_after_this == 1 and assigned_val == 0:
            split = "val"
            assigned_val += len(event_scene_ids)
        elif assigned_train < train_target:
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


def _normalise_filter_values(values: Iterable[str] | None) -> set[str]:
    return {value.strip().lower() for value in values or () if value.strip()}


def _record_matches_filters(
    record: dict[str, Any],
    disaster_names: set[str],
    disaster_types: set[str],
    scene_id: str,
) -> bool:
    disaster_name = str(record.get("disaster_name") or extract_disaster_name(scene_id)).lower()
    disaster_type = str(record.get("disaster_type") or infer_disaster_type(scene_id)).lower()
    if disaster_names and disaster_name not in disaster_names:
        return False
    return not (disaster_types and disaster_type not in disaster_types)


def write_scene_manifest_csv(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCENE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
