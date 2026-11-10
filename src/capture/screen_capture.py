"""
Screen Capture Engine.
High-speed screen capturing with multi-backend fallback:
1. mss (high performance)
2. PIL.ImageGrab (universal desktop fallback)
3. pyautogui (fallback)
"""

from __future__ import annotations
import os
import time
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import numpy as np
import cv2
import mss
from PIL import ImageGrab
import pyautogui
from src.calibration.viewport import ViewportCalibrator

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures game viewport frames with multi-backend fallback."""

    def __init__(self, calibrator: ViewportCalibrator, target_fps: float = 15.0, save_dir: str = "data/diagnostics"):
        self.calibrator = calibrator
        self.target_fps = target_fps
        self.frame_interval = 1.0 / max(1.0, target_fps)
        self.last_capture_time = 0.0
        self.save_dir = save_dir
        self.sct = None
        self.backend = "mss"
        os.makedirs(self.save_dir, exist_ok=True)
        self._init_mss()

    def _init_mss(self) -> None:
        try:
            self.sct = getattr(mss, "MSS", mss.mss)()
            self.backend = "mss"
        except Exception as e:
            logger.warning(f"MSS initialization failed ({e}), falling back to PIL.ImageGrab")
            self.backend = "pil"

    def capture_frame(self) -> np.ndarray:
        """Captures a single BGR frame cropped to the calibrated viewport."""
        now = time.time()
        elapsed = now - self.last_capture_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)

        monitor = self.calibrator.get_capture_box()
        frame_bgr = None

        # Method 1: MSS
        if self.backend == "mss" and self.sct is not None:
            try:
                sct_img = self.sct.grab(monitor)
                frame = np.array(sct_img)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception as e:
                logger.warning(f"MSS grab failed ({e}), falling back to PIL.ImageGrab")
                self.backend = "pil"

        # Method 2: PIL ImageGrab fallback
        if frame_bgr is None:
            try:
                bbox = (
                    monitor["left"],
                    monitor["top"],
                    monitor["left"] + monitor["width"],
                    monitor["top"] + monitor["height"]
                )
                pil_img = ImageGrab.grab(bbox=bbox)
                frame_np = np.array(pil_img)
                frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.warning(f"PIL grab failed ({e}), falling back to PyAutoGUI")
                try:
                    py_img = pyautogui.screenshot(region=(monitor["left"], monitor["top"], monitor["width"], monitor["height"]))
                    frame_np = np.array(py_img)
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                except Exception as e2:
                    logger.error(f"All screen capture backends failed: {e2}")
                    # Return blank 1920x1080 canvas
                    frame_bgr = np.zeros((1080, 1920, 3), dtype=np.uint8)

        self.last_capture_time = time.time()
        return frame_bgr

    def save_failure_screenshot(self, frame: np.ndarray, tag: str = "failure") -> str:
        """Saves a debug screenshot to disk and returns absolute path."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{tag}_{timestamp_str}.png"
        filepath = os.path.join(self.save_dir, filename)
        cv2.imwrite(filepath, frame)
        logger.info(f"Diagnostic screenshot saved to {filepath}")
        return filepath

    def close(self) -> None:
        if self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
