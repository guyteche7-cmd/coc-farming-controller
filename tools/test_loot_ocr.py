import cv2
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.vision.state_detector import UIStateDetector
from src.vision.loot_detector import LootDetector

img_path = r"assets/reference/media_1787468049167.jpg"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Screenshot size: {w}x{h}")

detector = UIStateDetector(use_ai=True)
state_res = detector.detect_ui_state(img)
print(f"Detected UI State: {state_res.value} ({state_res.confidence*100:.0f}%)")

if detector.ai and detector.last_ai_detections:
    print("\nYOLO Resource Detections:")
    for cls in ["gold", "elixir", "d_elixir"]:
        if cls in detector.last_ai_detections:
            for item in detector.last_ai_detections[cls]:
                print(f"  {cls}: bbox_pixel={item['bbox_pixel']}, conf={item['confidence']:.2f}")

loot_det = LootDetector()
res = loot_det.detect_candidate_loot(img)
print(f"\nLoot Result: Gold={res.value.gold:,}, Elixir={res.value.elixir:,}, DE={res.value.dark_elixir:,}")
