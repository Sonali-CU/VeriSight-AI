"""
Lightweight Audio Spoof CNN architecture for CPU execution.
Compliant with VeriSight AI CPU-only audio detection specification.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class AudioSpoofCNN(nn.Module):
    """
    Lightweight 2D CNN operating on normalized Log-Mel spectrograms.
    Architecture:
      Conv2D(1, 16, 3, pad=1) -> BN -> ReLU -> MaxPool2D(2)
      Conv2D(16, 32, 3, pad=1) -> BN -> ReLU -> MaxPool2D(2)
      Conv2D(32, 64, 3, pad=1) -> BN -> ReLU -> AdaptiveAvgPool2d((4, 4))
      Flatten -> Linear(1024, 64) -> ReLU -> Dropout(0.3) -> Linear(64, 2)
    Total parameters: ~75k, optimized for high throughput CPU inference.
    """

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.30),
            nn.Linear(64, 2)
        )

    def forward(self, x):
        return self.classifier(self.features(x))
