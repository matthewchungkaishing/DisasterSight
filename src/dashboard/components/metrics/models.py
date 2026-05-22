"""Data models for dashboard KPI metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricCell:
    """A single KPI shown in a grid or quadrant layout."""

    key: str
    label: str
    value_html: str
    value_class: str = ""
