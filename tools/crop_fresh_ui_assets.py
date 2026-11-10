import cv2
import os

img_path = r"assets/reference/media_1787464410731.png"
img = cv2.imread(img_path)
h, w, _ = img.shape
print(f"Uploaded screenshot size: {w}x{h}")

# Delete old assets requested by user
old_files = [
    "assets/ui/single_player_tab.png",
    "assets/ui/multiplayer_tab.png",
    "assets/ui/return_home_button.png"
]
for f in old_files:
    if os.path.exists(f):
        os.remove(f)
        print(f"Deleted old file: {f}")

# Crop Multiplayer Tab (Top-left tab)
# x: ~15 to 175 (0.015 to 0.175 of width)
# y: ~30 to 100 (0.030 to 0.100 of height)
mp_crop = img[int(h * 0.030):int(h * 0.100), int(w * 0.015):int(w * 0.175)]
cv2.imwrite("assets/ui/multiplayer_tab.png", mp_crop)
print(f"Saved fresh assets/ui/multiplayer_tab.png: {mp_crop.shape}")

# Crop Single Player Tab (Middle tab)
# x: ~178 to 338 (0.178 to 0.338 of width)
# y: ~30 to 100 (0.030 to 0.100 of height)
sp_crop = img[int(h * 0.030):int(h * 0.100), int(w * 0.178):int(w * 0.338)]
cv2.imwrite("assets/ui/single_player_tab.png", sp_crop)
print(f"Saved fresh assets/ui/single_player_tab.png: {sp_crop.shape}")

# Crop Find a Match Button (Yellow button under Battle card)
# x: ~45 to 250 (0.045 to 0.250 of width)
# y: ~645 to 760 (0.645 to 0.760 of height)
find_crop = img[int(h * 0.645):int(h * 0.760), int(w * 0.045):int(w * 0.250)]
cv2.imwrite("assets/ui/find_match_battle_button.png", find_crop)
print(f"Saved fresh assets/ui/find_match_battle_button.png: {find_crop.shape}")

# Copy clean Return Home template to return_home_button.png
if os.path.exists("assets/ui/victory_return_home_button.png"):
    v_img = cv2.imread("assets/ui/victory_return_home_button.png")
    cv2.imwrite("assets/ui/return_home_button.png", v_img)
    print("Saved fresh assets/ui/return_home_button.png from clean green Return Home template.")

print("All fresh assets successfully created and verified!")
