"""Data models for the Scene Explorer image viewer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePane:
    """A single image pane shown in the paired scene viewer."""

    key: str
    label: str
    src: str
    alt: str
    width: int | None = None
    height: int | None = None
