"""Paired pre/post-disaster building damage classifier."""

from __future__ import annotations

import torch
import torch.nn as nn
from torchvision import models
from torchvision.models import ResNet18_Weights

from src.common.constants import DAMAGE_CLASSES

NUM_CLASSES = len(DAMAGE_CLASSES)
PAIRED_IN_CHANNELS = 6


def _make_resnet18_backbone(pretrained: bool = True) -> models.ResNet:
    """Return a ResNet-18 with its first conv modified for 6-channel input."""
    weights = ResNet18_Weights.DEFAULT if pretrained else None
    backbone = models.resnet18(weights=weights)

    original_conv = backbone.conv1
    new_conv = nn.Conv2d(
        in_channels=PAIRED_IN_CHANNELS,
        out_channels=original_conv.out_channels,
        kernel_size=original_conv.kernel_size,
        stride=original_conv.stride,
        padding=original_conv.padding,
        bias=original_conv.bias is not None,
    )

    if pretrained:
        with torch.no_grad():
            w = original_conv.weight.data  # (64, 3, 7, 7)
            # Each half gets the full pretrained weights, scaled by 0.5 so the
            # expected activation magnitude stays the same as the original net.
            new_conv.weight.data = torch.cat([w, w], dim=1) * 0.5

    backbone.conv1 = new_conv
    return backbone


class PairedCropClassifier(nn.Module):
    """
    Lightweight classifier that takes a 6-channel paired tensor (pre + post
    crops concatenated along the channel axis) and predicts one of four xBD
    damage classes.

    Architecture:
      ResNet-18 backbone (6-ch input) -> 512-d features -> dropout -> 4-class logits
    """

    def __init__(self, pretrained: bool = True, dropout: float = 0.3) -> None:
        super().__init__()
        backbone = _make_resnet18_backbone(pretrained=pretrained)
        in_features = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.head = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """``x``: (B, 6, H, W) -> logits: (B, NUM_CLASSES)"""
        features = self.backbone(x)
        logits: torch.Tensor = self.head(features)
        return logits

    @torch.inference_mode()
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return softmax class probabilities. Automatically enters eval mode."""
        was_training = self.training
        self.eval()
        probs = torch.softmax(self.forward(x), dim=-1)
        self.train(was_training)
        return probs
