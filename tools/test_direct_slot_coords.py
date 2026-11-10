import cv2
import os
import sys

img_path = r"assets/reference/media_1787472608785.jpg"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Screenshot Resolution: {w}x{h}")

# In media_1787472608785.jpg:
# Bottom ribbon starts around x=100px (0.10) to x=600px (0.60), y=520px (0.90)
# Let's draw visual markers for 7 slots and target deployment point (0.400, 0.050)

slot_centers_x = [0.106, 0.185, 0.265, 0.345, 0.425, 0.505, 0.585]
ribbon_y = 0.900
target_deploy = (0.400, 0.050)

vis = img.copy()

# Draw target deploy point
tx, ty = int(target_deploy[0] * w), int(target_deploy[1] * h)
cv2.circle(vis, (tx, ty), 15, (0, 0, 255), -1)
cv2.putText(vis, "DEPLOY POINT Beside Battle ends in", (tx + 20, ty + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

# Draw ribbon slot markers
for idx, sx in enumerate(slot_centers_x):
    px, py = int(sx * w), int(ribbon_y * h)
    cv2.circle(vis, (px, py), 12, (0, 255, 0), -1)
    cv2.putText(vis, f"S{idx}", (px - 10, py - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

os.makedirs("data/diagnostics", exist_ok=True)
out_path = "data/diagnostics/direct_deploy_verification.png"
cv2.imwrite(out_path, vis)
print(f"Saved slot and deployment point verification image to: {out_path}")
