"""
AI Vision Perception Engine (YOLOv8).
Integrates pre-trained YOLO model (best.pt) to detect dynamic in-game UI buttons,
resource bars, storages, and collectors across any windowed or fullscreen resolution.
"""

from __future__ import annotations
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2
from ultralytics import YOLO
import torch

try:
    torch.set_num_threads(1)
except Exception:
    pass

logger = logging.getLogger(__name__)

# Global singleton to prevent reloading model into memory multiple times
_SHARED_YOLO_MODEL: Optional[YOLO] = None


def get_shared_yolo(model_path: str = "assets/models/best.pt") -> Optional[YOLO]:
    global _SHARED_YOLO_MODEL
    if _SHARED_YOLO_MODEL is None:
        if not os.path.exists(model_path):
            # Fallback path check
            alt_path = os.path.join(os.path.dirname(__file__), "../../assets/models/best.pt")
            if os.path.exists(alt_path):
                model_path = os.path.abspath(alt_path)
            else:
                logger.warning(f"YOLO model file not found at {model_path}")
                return None
        try:
            logger.info(f"Loading YOLOv8 model from {model_path}...")
            _SHARED_YOLO_MODEL = YOLO(model_path)
            logger.info("YOLOv8 model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return None
    return _SHARED_YOLO_MODEL


class AIVisionDetector:
    """
    Performs AI object detection on game frames using YOLOv8.
    Returns pixel coordinates and normalized (0.0 to 1.0) coordinates for dynamic clicking.
    """

    def __init__(self, model_path: str = "assets/models/best.pt", conf: float = 0.30):
        self.model_path = model_path
        self.conf = conf
        self.model = get_shared_yolo(model_path)

    def is_ready(self) -> bool:
        return self.model is not None

    def detect(self, frame_bgr: np.ndarray, target_classes: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Runs YOLO inference on the given frame.

        Returns:
            Dict mapping class_name -> list of detection dicts:
            {
                "center_pixel": (cx, cy),
                "center_norm": (nx, ny),
                "bbox_pixel": (x1, y1, x2, y2),
                "bbox_norm": (nx1, ny1, nx2, ny2),
                "confidence": float
            }
        """
        if self.model is None or frame_bgr is None or frame_bgr.size == 0:
            return {}

        h, w, _ = frame_bgr.shape
        if h == 0 or w == 0:
            return {}

        try:
            results = self.model.predict(source=frame_bgr, conf=self.conf, verbose=False)
        except Exception as e:
            logger.error(f"YOLO prediction error: {e}")
            return {}

        detections: Dict[str, List[Dict[str, Any]]] = {}

        if not results or len(results) == 0:
            return detections

        for box in results[0].boxes:
            class_id = int(box.cls.item())
            class_name = str(self.model.names.get(class_id, class_id))
            conf_val = float(box.conf.item())

            if target_classes and class_name not in target_classes:
                continue

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            # Clip bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            cx = int(x1 + (x2 - x1) / 2)
            cy = int(y1 + (y2 - y1) / 2)

            nx = float(cx) / float(w)
            ny = float(cy) / float(h)

            entry = {
                "center_pixel": (cx, cy),
                "center_norm": (nx, ny),
                "bbox_pixel": (x1, y1, x2, y2),
                "bbox_norm": (x1 / float(w), y1 / float(h), x2 / float(w), y2 / float(h)),
                "confidence": conf_val,
                "class_name": class_name
            }

            if class_name not in detections:
                detections[class_name] = []
            detections[class_name].append(entry)

        return detections

    def get_button_normalized_center(self, frame_bgr: np.ndarray, class_name: str) -> Optional[Tuple[float, float]]:
        """Finds the highest-confidence occurrence of a button class and returns its normalized center (nx, ny)."""
        dets = self.detect(frame_bgr, target_classes=[class_name])
        if class_name in dets and dets[class_name]:
            best = max(dets[class_name], key=lambda x: x["confidence"])
            return best["center_norm"]
        return None

    def get_resource_boxes(self, frame_bgr: np.ndarray) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """Returns pixel bounding boxes for gold, elixir, d_elixir for targeted OCR."""
        target_res = ["gold", "elixir", "d_elixir", "post_gold", "post_elixir", "post_d_elixir"]
        dets = self.detect(frame_bgr, target_classes=target_res)
        res_boxes = {}
        for cls_name, items in dets.items():
            res_boxes[cls_name] = [item["bbox_pixel"] for item in items]
        return res_boxes

    def get_detected_storages(self, frame_bgr: np.ndarray) -> List[Tuple[float, float]]:
        """Returns list of normalized centers for all detected gold/elixir/dark elixir storages on map."""
        storage_classes = ["golds", "elixirs", "d_elixirs"]
        dets = self.detect(frame_bgr, target_classes=storage_classes)
        centers = []
        for cls_name in storage_classes:
            if cls_name in dets:
                for item in dets[cls_name]:
                    centers.append(item["center_norm"])
        return centers
