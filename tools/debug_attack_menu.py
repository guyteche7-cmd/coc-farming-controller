import sys, os
sys.path.insert(0, os.path.abspath("."))
import cv2
import numpy as np
from src.vision.state_detector import UIStateDetector

img = cv2.imread(r"assets/reference/media_1787434896917.jpg")
h, w, _ = img.shape
print(f"Attack menu screenshot size: {w}x{h}")

# Crop CoC window canvas (excluding title bar / border if any, or whole image if fullscreen window)
# In this screenshot (1024x576), CoC client area is roughly from (4, 44) to (1020, 572)
# Let's inspect the whole image and window area
detector = UIStateDetector()
res = detector.detect_ui_state(img)
print(f"Detected UI state: {res.value} (confidence: {res.confidence:.2f})")

print("\n--- Template Matching Scores on Attack Menu Screenshot ---")
for name, tmpl in sorted(detector.templates.items()):
    res_match = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res_match)
    print(f"Template '{name:30s}': score = {max_val:.3f} at {max_loc}")
