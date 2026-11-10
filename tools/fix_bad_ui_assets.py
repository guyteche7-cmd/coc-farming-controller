import cv2
import os

print("Fixing mislabeled/incorrect UI template assets...")

# 1. return_home_button.png: replace with victory_return_home_button.png (which is the actual clean green Return Home button!)
v_path = "assets/ui/victory_return_home_button.png"
v_img = cv2.imread(v_path)
if v_img is not None:
    cv2.imwrite("assets/ui/return_home_button.png", v_img)
    print("Fixed assets/ui/return_home_button.png using clean green Return Home template.")

# 2. Extract clean Multiplayer tab and Single Player tab from full screen ref_1.png
ref_path = r"temp\ref_1.png"
ref_img = cv2.imread(ref_path)
if ref_img is not None:
    h, w, _ = ref_img.shape
    # If ref_img has attack menu popup open or game elements
    # Let's inspect where tabs are
    print(f"Loaded ref_1.png size: {w}x{h}")

print("Asset replacement complete!")
