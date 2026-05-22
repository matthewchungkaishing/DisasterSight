"""PyTorch Dataset for paired pre/post building crops loaded from a crop manifest CSV."""

from __future__ import annotations

import csv
import logging
import random
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import torch
import torchvision.transforms.functional as TF
from PIL import Image
from torch import Tensor
from torch.utils.data import Dataset, WeightedRandomSampler
from torchvision import transforms

from src.common.constants import CLASS_TO_INDEX, DAMAGE_CLASSES

log = logging.getLogger(__name__)

_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)
NUM_CLASSES = len(DAMAGE_CLASSES)


def _normalize_transform(image_size: int) -> transforms.Compose:
    """Deterministic resize + tensor + normalise (no stochastic ops)."""
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
        ]
    )


class CropDataset(Dataset):
    """
    Yields ``(paired_tensor, label_index)`` tuples from a validated crop manifest.

    ``paired_tensor`` has shape ``(6, H, W)``: pre-image channels followed by
    post-image channels, ready for a 6-channel backbone input.

    Geometric augmentations (flip) are applied **synchronously** to both the
    pre and post image so spatial correspondence is preserved.  Color jitter is
    applied independently since illumination can legitimately differ between
    acquisition dates.
    """

    def __init__(
        self,
        manifest_path: Path | None,
        split: str,
        image_size: int = 224,
        *,
        augment: bool = False,
        project_root: Path | None = None,
        records: list[dict[str, str]] | None = None,
    ) -> None:
        from src.common.paths import PROJECT_ROOT

        self.split = split
        self.project_root = project_root or PROJECT_ROOT
        self.image_size = image_size
        self.augment = augment
        self._base_transform = _normalize_transform(image_size)
        if augment:
            self._color_jitter = transforms.ColorJitter(
                brightness=0.2,
                contrast=0.2,
                saturation=0.1,
            )
        if records is None:
            if manifest_path is None:
                raise ValueError("manifest_path is required when records are not provided.")
            self._records = self._load_records(manifest_path, split)
        else:
            self._records = list(records)
        self.label_indices: list[int] = [CLASS_TO_INDEX[r["damage_label"]] for r in self._records]

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, idx: int) -> tuple[Tensor, int]:
        record = self._records[idx]
        try:
            pre_img = self._open_rgb(record["pre_crop_path"])
            post_img = self._open_rgb(record["post_crop_path"])
        except (FileNotFoundError, OSError) as exc:
            raise RuntimeError(
                f"Failed to load crops for record {idx} "
                f"(scene={record.get('scene_id')}, building={record.get('building_id')}): {exc}"
            ) from exc

        if self.augment:
            pre_img, post_img = self._sync_augment(pre_img, post_img)

        pre_tensor = self._base_transform(pre_img)
        post_tensor = self._base_transform(post_img)
        paired = torch.cat([pre_tensor, post_tensor], dim=0)  # (6, H, W)
        return paired, self.label_indices[idx]

    # ------------------------------------------------------------------
    # Augmentation — geometric ops are synchronised, colour ops are not
    # ------------------------------------------------------------------

    def _sync_augment(self, pre: Image.Image, post: Image.Image) -> tuple[Image.Image, Image.Image]:
        if random.random() > 0.5:
            pre = TF.hflip(pre)
            post = TF.hflip(post)
        if random.random() > 0.5:
            pre = TF.vflip(pre)
            post = TF.vflip(post)
        # Color jitter applied independently — different acquisition conditions.
        pre = self._color_jitter(pre)
        post = self._color_jitter(post)
        return pre, post

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

    def _open_rgb(self, path_value: str) -> Image.Image:
        path = Path(path_value)
        if not path.is_absolute():
            path = self.project_root / path
        return Image.open(path).convert("RGB")

    @staticmethod
    def _load_records(manifest_path: Path, split: str) -> list[dict[str, str]]:
        with manifest_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader if row.get("split") == split]


# ------------------------------------------------------------------
# Class-weight helpers
# ------------------------------------------------------------------


def compute_class_weights(label_indices: Sequence[int], num_classes: int) -> Tensor:
    """
    Inverse-frequency class weights for ``CrossEntropyLoss``.

    Under-represented classes receive higher weights so the loss treats each
    class equally regardless of sample count.
    """
    counts = Counter(label_indices)
    total = len(label_indices)
    if total == 0:
        return torch.ones(num_classes, dtype=torch.float32)

    weights = torch.zeros(num_classes, dtype=torch.float32)
    for class_idx in range(num_classes):
        n = counts.get(class_idx, 0)
        weights[class_idx] = total / (num_classes * n) if n > 0 else float(total)
    return weights


def make_weighted_sampler(label_indices: Sequence[int], num_classes: int) -> WeightedRandomSampler:
    """
    ``WeightedRandomSampler`` that draws each class with equal expected
    frequency per epoch, compensating for heavy class imbalance in xBD crops.
    """
    class_weights = compute_class_weights(label_indices, num_classes)
    sample_weights = torch.tensor(
        [class_weights[idx].item() for idx in label_indices], dtype=torch.float32
    )
    return WeightedRandomSampler(
        weights=sample_weights.tolist(),
        num_samples=len(label_indices),
        replacement=True,
    )


def class_distribution_summary(label_indices: Sequence[int]) -> dict[str, int]:
    """Human-readable class-count dict keyed by damage label name."""
    counts = Counter(label_indices)
    return {DAMAGE_CLASSES[i]: counts.get(i, 0) for i in range(NUM_CLASSES)}
