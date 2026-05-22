"""Confusion matrix display component."""

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.common.constants import DAMAGE_CLASSES
from src.dashboard.artifact_resolver import resolve_confusion_matrix_image
from src.dashboard.labels import display_label


def render(matrix: list[list[float]] | None = None, labels: list[str] | None = None) -> None:
    """Show a pre-rendered confusion-matrix image or generate a heatmap."""
    img_path = resolve_confusion_matrix_image()
    if img_path:
        st.image(str(img_path), use_container_width=True)
        return

    if not matrix:
        st.info("Confusion matrix not available.")
        return

    labels = labels or list(DAMAGE_CLASSES)
    display_labels = [display_label(lbl) for lbl in labels]
    data = np.array(matrix)

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor("#161B22")
    ax.set_facecolor("#161B22")
    im = ax.imshow(data, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(display_labels)))
    ax.set_yticks(range(len(display_labels)))
    ax.set_xticklabels(display_labels, rotation=45, ha="right", color="#9AA8BC", fontsize=8)
    ax.set_yticklabels(display_labels, color="#9AA8BC", fontsize=8)
    ax.set_xlabel("Predicted Label", color="#9AA8BC")
    ax.set_ylabel("True Label", color="#9AA8BC")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(
                j,
                i,
                f"{data[i, j]:.2f}",
                ha="center",
                va="center",
                color="#E8EDF4",
                fontsize=9,
            )
    plt.colorbar(im, ax=ax, fraction=0.046)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    st.image(buf, use_container_width=True)


def confusion_matrix_csv(matrix: list[list[float]], labels: list[str]) -> str:
    """Serialize a confusion matrix to CSV for download."""
    header = "true_label," + ",".join(labels)
    rows = [f"{labels[i]}," + ",".join(str(v) for v in matrix[i]) for i in range(len(labels))]
    return "\n".join([header, *rows])
