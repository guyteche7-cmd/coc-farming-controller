import os
import cv2
import numpy as np

img_active_win = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787425068791.jpg")
img_end_dialog = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787425068743.jpg")
img_victory = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787425068758.jpg")

# Save reference full screens
cv2.imwrite("assets/test_cases/screen_10_active_battle_win.png", img_active_win)
cv2.imwrite("assets/test_cases/screen_11_end_battle_dialog.png", img_end_dialog)
cv2.imwrite("assets/test_cases/screen_12_victory_result.png", img_victory)

# --- 1. ACTIVE BATTLE WIN CROPS ---
h, w, _ = img_active_win.shape
# "End Battle" button in bottom left
end_battle_active_btn = img_active_win[int(h*0.755):int(h*0.825), int(w*0.010):int(w*0.110)]
cv2.imwrite("assets/ui/end_battle_active_button.png", end_battle_active_btn)

# Overall Damage 73% (2 stars)
damage_win_box = img_active_win[int(h*0.740):int(h*0.815), int(w*0.840):int(w*0.990)]
cv2.imwrite("assets/ui/overall_damage_win_panel.png", damage_win_box)

# --- 2. END BATTLE DIALOG CROPS ---
h, w, _ = img_end_dialog.shape
# Dialog Title "End Battle?"
end_battle_title = img_end_dialog[int(h*0.300):int(h*0.370), int(w*0.410):int(w*0.590)]
cv2.imwrite("assets/ui/dialog_end_battle_title.png", end_battle_title)

# --- 3. VICTORY SCREEN CROPS ---
h, w, _ = img_victory.shape
# "Victory" banner
victory_banner = img_victory[int(h*0.270):int(h*0.335), int(w*0.430):int(w*0.570)]
cv2.imwrite("assets/ui/victory_banner.png", victory_banner)

# Return Home button
victory_return_home = img_victory[int(h*0.810):int(h*0.920), int(w*0.420):int(w*0.570)]
cv2.imwrite("assets/ui/victory_return_home_button.png", victory_return_home)

print("Victory and End Battle templates extracted successfully!")
