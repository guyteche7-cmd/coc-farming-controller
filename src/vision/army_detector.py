"""
Army Deployment Ribbon Detector.
Detects deployment slots, unit categories, and remaining unit quantities in the bottom ribbon.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from src.state.game_state import DetectionResult, BoundingBox
from src.vision.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class ArmyDetector:
    """Detects unit cards in the bottom deployment ribbon (y: 0.85 - 0.99)."""

    def __init__(self, ocr_engine: Optional[OCREngine] = None):
        self.ocr = ocr_engine or OCREngine()

    def detect_army_ribbon(self, frame_bgr: np.ndarray, expected_slots_count: int = 7) -> DetectionResult[List[Dict[str, Any]]]:
        h, w, _ = frame_bgr.shape
        if h == 0 or w == 0:
            return DetectionResult(value=[], confidence=0.0, errors=["Empty frame"])

        ribbon_y1 = int(h * 0.85)
        ribbon_y2 = int(h * 0.99)
        ribbon_x1 = int(w * 0.05)
        ribbon_x2 = int(w * 0.88)

        ribbon_crop = frame_bgr[ribbon_y1:ribbon_y2, ribbon_x1:ribbon_x2]
        rh, rw, _ = ribbon_crop.shape

        detected_slots = []
        if expected_slots_count <= 0:
            expected_slots_count = 7

        slot_w = rw // expected_slots_count

        for i in range(expected_slots_count):
            sx1 = i * slot_w
            sx2 = min(rw, (i + 1) * slot_w)
            slot_img = ribbon_crop[:, sx1:sx2]

            # The digit badge is usually located at the bottom or top corner of the unit icon
            badge_crop = slot_img[int(rh * 0.60):rh, 0:int(slot_w * 0.70)]
            qty_val, qty_conf = self.ocr.read_integer(badge_crop)

            global_bbox = BoundingBox(
                x=ribbon_x1 + sx1,
                y=ribbon_y1,
                width=slot_w,
                height=rh
            )

            slot_data = {
                "slot_index": i,
                "quantity": qty_val if qty_val is not None else 1,
                "bbox": global_bbox.model_dump(),
                "confidence": qty_conf if qty_conf > 0 else 0.80
            }
            detected_slots.append(slot_data)

        return DetectionResult(
            value=detected_slots,
            confidence=0.85,
            bbox=BoundingBox(x=ribbon_x1, y=ribbon_y1, width=rw, height=rh)
        )
