import sys, os
sys.path.insert(0, os.path.abspath("."))
import cv2
from src.vision.state_detector import UIStateDetector

img_path = r"assets/reference/media_1787459793239.png"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"My Army screenshot dimensions: {w}x{h}")

detector = UIStateDetector(use_ai=True)
if detector.ai and detector.ai.is_ready():
    dets = detector.ai.detect(img)
    print("\n--- YOLO Detections ---")
    for cls_name, items in dets.items():
        print(f"Class: {cls_name} -> {len(items)} items:")
        for itm in items:
            print(f"   conf={itm['confidence']:.2f}, bbox_norm={itm['bbox_norm']}, center_norm={itm['center_norm']}")

res = detector.detect_ui_state(img)
print(f"\nResulting UI State: {res.value} ({res.confidence:.2f})")
print("Dynamic anchors:", detector.dynamic_anchors)
