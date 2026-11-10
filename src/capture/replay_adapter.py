"""
Replay Screen Adapter.
Feeds recorded images/screenshots into the perception engine for offline testing
and headless regression runs without requiring live game input.
"""

from __future__ import annotations
import os
import glob
import logging
from typing import List, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ReplayScreenAdapter:
    """Simulates a screen capture feed from a sequence or folder of images."""

    def __init__(self, image_paths: Optional[List[str]] = None, directory: Optional[str] = None):
        self.frames: List[np.ndarray] = []
        self.current_idx = 0

        if image_paths:
            for p in image_paths:
                if os.path.exists(p):
                    img = cv2.imread(p)
                    if img is not None:
                        self.frames.append(img)
        elif directory and os.path.exists(directory):
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
                for p in sorted(glob.glob(os.path.join(directory, ext))):
                    img = cv2.imread(p)
                    if img is not None:
                        self.frames.append(img)

        if not self.frames:
            # Fallback placeholder 1920x1080 frame
            logger.warning("No images loaded into ReplayScreenAdapter. Creating blank 1920x1080 frame.")
            self.frames.append(np.zeros((1080, 1920, 3), dtype=np.uint8))

    def capture_frame(self) -> np.ndarray:
        """Returns the next frame in the replay sequence."""
        if not self.frames:
            return np.zeros((1080, 1920, 3), dtype=np.uint8)

        frame = self.frames[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.frames)
        return frame

    def set_frame(self, frame: np.ndarray) -> None:
        """Sets a single active frame directly."""
        self.frames = [frame]
        self.current_idx = 0

    def reset(self) -> None:
        self.current_idx = 0
