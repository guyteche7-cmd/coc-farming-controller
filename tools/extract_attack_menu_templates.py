import cv2
import os

img = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787434896917.jpg")
h, w, _ = img.shape
print(f"Loaded image: {w}x{h}")

os.makedirs("assets/ui", exist_ok=True)

# 1. Extract multiplayer_tab
# Tab at top-left: x from 55 to 205, y from 68 to 135
tab = img[68:135, 55:205]
cv2.imwrite("assets/ui/multiplayer_tab.png", tab)
print("Saved assets/ui/multiplayer_tab.png:", tab.shape)

# 2. Extract find_match_battle_button
# Yellow button on Battle card: x from 88 to 276, y from 375 to 445
btn = img[375:445, 88:276]
cv2.imwrite("assets/ui/find_match_battle_button.png", btn)
print("Saved assets/ui/find_match_battle_button.png:", btn.shape)

# 3. Extract single_player_tab & practice_tab for complete coverage
single_tab = img[68:135, 215:365]
cv2.imwrite("assets/ui/single_player_tab.png", single_tab)
print("Saved assets/ui/single_player_tab.png:", single_tab.shape)

print("Extraction complete!")
