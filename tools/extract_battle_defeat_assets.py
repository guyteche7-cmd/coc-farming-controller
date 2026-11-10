import os
import cv2
import numpy as np

img_battle = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787424069354.jpg")
img_dialog = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787424069134.jpg")
img_defeat = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787424069258.jpg")

# Save reference full screens
cv2.imwrite("assets/test_cases/screen_7_active_battle.png", img_battle)
cv2.imwrite("assets/test_cases/screen_8_surrender_dialog.png", img_dialog)
cv2.imwrite("assets/test_cases/screen_9_defeat_result.png", img_defeat)

# --- 1. ACTIVE BATTLE SCREEN CROPS ---
h, w, _ = img_battle.shape
# Surrender Button (Bottom-Left: x: 10 to 110, y: 435 to 470 in 1024x575)
surrender_btn = img_battle[int(h*0.755):int(h*0.825), int(w*0.010):int(w*0.110)]
cv2.imwrite("assets/ui/surrender_button.png", surrender_btn)
print(f"Surrender Button: shape {surrender_btn.shape}, norm center: ({(0.010+0.110)/2:.3f}, {(0.755+0.825)/2:.3f})")

# Overall Damage Box (Bottom-Right: x: 860 to 990, y: 425 to 465)
overall_damage = img_battle[int(h*0.740):int(h*0.815), int(w*0.840):int(w*0.990)]
cv2.imwrite("assets/ui/overall_damage_panel.png", overall_damage)

# Damage percentage number only (x: 940 to 990, y: 440 to 465)
damage_percent_num = img_battle[int(h*0.765):int(h*0.815), int(w*0.930):int(w*0.990)]
cv2.imwrite("assets/ui/damage_percent_num.png", damage_percent_num)

# Battle Timer (Top-Center: x: 440 to 550, y: 5 to 45)
battle_ends_in = img_battle[int(h*0.010):int(h*0.080), int(w*0.440):int(w*0.550)]
cv2.imwrite("assets/ui/battle_ends_in_timer.png", battle_ends_in)

# --- 2. SURRENDER DIALOG CROPS ---
h, w, _ = img_dialog.shape
# Dialog Title "Surrender?"
surrender_title = img_dialog[int(h*0.300):int(h*0.370), int(w*0.410):int(w*0.590)]
cv2.imwrite("assets/ui/dialog_surrender_title.png", surrender_title)

# Orange "Cancel" button (x: 330 to 495, y: 320 to 390 in 1024x575)
btn_cancel = img_dialog[int(h*0.555):int(h*0.680), int(w*0.320):int(w*0.490)]
cv2.imwrite("assets/ui/dialog_cancel_button.png", btn_cancel)
print(f"Cancel Dialog Button: shape {btn_cancel.shape}, norm center: ({(0.320+0.490)/2:.3f}, {(0.555+0.680)/2:.3f})")

# Green "Okay" button (x: 520 to 685, y: 320 to 390 in 1024x575)
btn_okay = img_dialog[int(h*0.555):int(h*0.680), int(w*0.510):int(w*0.675)]
cv2.imwrite("assets/ui/dialog_okay_button.png", btn_okay)
print(f"Okay Dialog Button: shape {btn_okay.shape}, norm center: ({(0.510+0.675)/2:.3f}, {(0.555+0.680)/2:.3f})")

# --- 3. DEFEAT / RESULT SCREEN CROPS ---
h, w, _ = img_defeat.shape
# "Defeat" banner
defeat_banner = img_defeat[int(h*0.270):int(h*0.335), int(w*0.430):int(w*0.570)]
cv2.imwrite("assets/ui/defeat_banner.png", defeat_banner)

# Green "Return Home" button (Bottom-Center: x: 430 to 570, y: 465 to 525 in 1024x575)
return_home_btn = img_defeat[int(h*0.810):int(h*0.920), int(w*0.420):int(w*0.570)]
cv2.imwrite("assets/ui/return_home_button.png", return_home_btn)
print(f"Return Home Button: shape {return_home_btn.shape}, norm center: ({(0.420+0.570)/2:.3f}, {(0.810+0.920)/2:.3f})")

print("All active battle, surrender dialog, and defeat result templates extracted successfully!")
