import cv2
import os

img_path = r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787473061447.jpg"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Screenshot Resolution: {w}x{h}")

# Target deploy point from user red mark: (0.6055, 0.0712)
target_deploy = (0.6055, 0.0712)
slot_centers_x = [0.106, 0.185, 0.265, 0.345, 0.425, 0.505, 0.585]
ribbon_y = 0.900

vis = img.copy()

# Draw primary deploy point and search offsets
probe_offsets = [
    (0.0, 0.0),
    (0.020, 0.010),
    (0.035, 0.020),
    (-0.015, -0.005),
    (0.010, -0.015),
    (0.045, 0.025)
]

for idx, (ox, oy) in enumerate(probe_offsets):
    px = int((target_deploy[0] + ox) * w)
    py = int((target_deploy[1] + oy) * h)
    color = (0, 255, 0) if idx == 0 else (255, 255, 0)
    cv2.circle(vis, (px, py), 8 if idx > 0 else 14, color, -1)

cv2.putText(vis, "TARGET DEPLOY SPOT & DIRECTION PROBES", (int(target_deploy[0]*w) - 150, int(target_deploy[1]*h) - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

# Draw ribbon slot markers
for idx, sx in enumerate(slot_centers_x):
    px, py = int(sx * w), int(ribbon_y * h)
    cv2.circle(vis, (px, py), 12, (0, 255, 0), -1)
    cv2.putText(vis, f"S{idx}", (px - 10, py - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

os.makedirs("data/diagnostics", exist_ok=True)
out_path = "data/diagnostics/red_spot_verification.png"
cv2.imwrite(out_path, vis)
print(f"Saved verification image to: {out_path}")
