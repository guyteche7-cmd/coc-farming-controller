import cv2
import numpy as np

img_path = r"C:\Users\ayush\.gemini\antigravity\scratch\coc-farming-controller\temp\deployment_pattern.png"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Image size: {w}x{h}")

# The bottom ribbon is located at y = 880 to 1040 in 1080p frame (y_norm = 0.88 to 0.96)
# Let's verify slot centers:
slots_px = [
    (int(w * 0.173), int(h * 0.900)), # Slot 0: Valkyrie
    (int(w * 0.240), int(h * 0.900)), # Slot 1: Log Launcher
    (int(w * 0.306), int(h * 0.900)), # Slot 2: Hero 1
    (int(w * 0.373), int(h * 0.900)), # Slot 3: Hero 2
    (int(w * 0.440), int(h * 0.900)), # Slot 4: Hero 3
    (int(w * 0.506), int(h * 0.900)), # Slot 5: Hero 4
    (int(w * 0.573), int(h * 0.900)), # Slot 6: Earthquake Spell
]

vis = img.copy()
for i, (cx, cy) in enumerate(slots_px):
    cv2.circle(vis, (cx, cy), 12, (0, 255, 0), 3)
    cv2.putText(vis, f"S{i}", (cx - 10, cy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

cv2.imwrite("data/diagnostics/slot_verification.png", vis)
print("Saved data/diagnostics/slot_verification.png for slot verification.")
