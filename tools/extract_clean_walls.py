import os
import cv2
import numpy as np

img_clean_walls = cv2.imread(r"assets/reference/media_1787426671623.png")

h, w, _ = img_clean_walls.shape
print(f"Clean wall chart shape: {w}x{h}")

# Level 18 (Dark stone, gold top - perfectly clean)
w18 = img_clean_walls[int(h*0.65):int(h*0.95), int(w*0.62):int(w*0.80)]
cv2.imwrite("assets/walls/wall_level_18.png", w18)

# Level 19 (Dark purple/gold trim - perfectly clean)
w19 = img_clean_walls[int(h*0.65):int(h*0.95), int(w*0.80):int(w*0.99)]
cv2.imwrite("assets/walls/wall_level_19.png", w19)

print("Updated Level 18 and Level 19 wall templates with clean, unobstructed crops!")
