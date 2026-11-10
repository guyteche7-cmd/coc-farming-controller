import cv2
import numpy as np

img_path = r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787473061447.jpg"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Image Resolution: {w}x{h}")

# Detect the red circle drawn by the user
# In HSV: Red has two ranges
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask1 = cv2.inRange(hsv, np.array([0, 150, 150]), np.array([10, 255, 255]))
mask2 = cv2.inRange(hsv, np.array([170, 150, 150]), np.array([180, 255, 255]))
red_mask = mask1 | mask2

# Exclude bottom-left End Battle button (which is red) and top ribbon
# Focus on upper half
mask_upper = red_mask.copy()
mask_upper[int(h*0.3):, :] = 0  # Only look at top 30%

contours, _ = cv2.findContours(mask_upper, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area > 100:
        M = cv2.moments(cnt)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            nx = cx / w
            ny = cy / h
            print(f"Detected User Red Mark at pixel: ({cx}, {cy}) -> Normalized: ({nx:.4f}, {ny:.4f}), Area={area}")

