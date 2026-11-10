import os
import cv2
import numpy as np

img_chart = cv2.imread(r"assets/reference/media_1787426237763.png")
os.makedirs("assets/walls", exist_ok=True)

h, w, _ = img_chart.shape
print(f"Wall chart shape: {w}x{h}")

# The chart has 3 rows and 6 columns of wall levels (Levels 1 to 19)
# Row 2 (Levels 7 to 12)
# Row 3 (Levels 13 to 19)

# Save reference wall chart
cv2.imwrite("assets/test_cases/wall_levels_chart.png", img_chart)

# Extract Level 14, 15, 16, 17, 18, 19
# Row 3: y from 0.65 to 0.95
# Cols:
# L13: x ~ 0.00 to 0.16
# L14: x ~ 0.16 to 0.32
# L15: x ~ 0.32 to 0.48
# L16: x ~ 0.48 to 0.64
# L17: x ~ 0.64 to 0.80
# L18: x ~ 0.78 to 0.90
# L19: x ~ 0.88 to 1.00

# Level 15 (Town Hall 14 wall - gold/purple)
w15 = img_chart[int(h*0.65):int(h*0.95), int(w*0.30):int(w*0.48)]
cv2.imwrite("assets/walls/wall_level_15.png", w15)

# Level 16 (Town Hall 15 wall - teal/purple)
w16 = img_chart[int(h*0.65):int(h*0.95), int(w*0.48):int(w*0.65)]
cv2.imwrite("assets/walls/wall_level_16.png", w16)

# Level 17 (Town Hall 16 wall - white/gold/red)
w17 = img_chart[int(h*0.65):int(h*0.95), int(w*0.64):int(w*0.79)]
cv2.imwrite("assets/walls/wall_level_17.png", w17)

# Level 18 (Town Hall 17 wall - dark stone/gold)
w18 = img_chart[int(h*0.65):int(h*0.95), int(w*0.77):int(w*0.90)]
cv2.imwrite("assets/walls/wall_level_18.png", w18)

# Level 19 (Max wall)
w19 = img_chart[int(h*0.65):int(h*0.95), int(w*0.88):int(w*0.99)]
cv2.imwrite("assets/walls/wall_level_19.png", w19)

print("Extracted High-Level Wall Assets (L15-L19) into assets/walls/")
