import os
import cv2
import numpy as np

# Load the user images
img_home = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423034479.jpg")
img_attack_menu = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423034404.jpg")
img_my_army = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423139039.png")
img_clouds = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423300906.png")

os.makedirs("assets/ui", exist_ok=True)
os.makedirs("assets/army", exist_ok=True)
os.makedirs("assets/test_cases", exist_ok=True)

# Save reference full screens
cv2.imwrite("assets/test_cases/screen_1_home.png", img_home)
cv2.imwrite("assets/test_cases/screen_2_attack_menu.png", img_attack_menu)
cv2.imwrite("assets/test_cases/screen_3_my_army.png", img_my_army)
cv2.imwrite("assets/test_cases/screen_4_clouds.png", img_clouds)

# --- 1. HOME SCREEN CROPS ---
h, w, _ = img_home.shape
# Attack Button in bottom left (x: 10 to 100, y: 475 to 565 in 1024x575)
attack_btn_crop = img_home[int(h*0.835):int(h*0.975), int(w*0.012):int(w*0.100)]
cv2.imwrite("assets/ui/home_attack_button.png", attack_btn_crop)
print(f"Home Attack Button: shape {attack_btn_crop.shape}, norm pos: (0.056, 0.905)")

# Builder HUD (x: 450 to 520, y: 10 to 50)
builder_hud_crop = img_home[int(h*0.015):int(h*0.090), int(w*0.440):int(w*0.530)]
cv2.imwrite("assets/ui/builder_hud.png", builder_hud_crop)

# Storage HUD (Gold/Elixir/Dark Elixir top right)
storage_hud_crop = img_home[int(h*0.030):int(h*0.250), int(w*0.820):int(w*0.990)]
cv2.imwrite("assets/ui/storage_hud.png", storage_hud_crop)

# --- 2. ATTACK MENU (MULTIPLAYER) CROPS ---
h, w, _ = img_attack_menu.shape
# "Find a Match" under Battle (left card) (x: 45 to 240, y: 360 to 445 in 1024x575)
find_match_battle_btn = img_attack_menu[int(h*0.640):int(h*0.770), int(w*0.045):int(w*0.240)]
cv2.imwrite("assets/ui/find_match_battle_button.png", find_match_battle_btn)
print(f"Find a Match (Battle) Button: shape {find_match_battle_btn.shape}, norm pos: (0.142, 0.705)")

# "Multiplayer" tab header
multiplayer_tab = img_attack_menu[int(h*0.030):int(h*0.100), int(w*0.015):int(w*0.170)]
cv2.imwrite("assets/ui/multiplayer_tab.png", multiplayer_tab)

# --- 3. MY ARMY SCREEN CROPS ---
h, w, _ = img_my_army.shape
# Green "Attack!" button at bottom right (x: 755 to 930, y: 470 to 535 in 1024x561)
army_attack_btn = img_my_army[int(h*0.840):int(h*0.955), int(w*0.740):int(w*0.910)]
cv2.imwrite("assets/ui/army_screen_attack_button.png", army_attack_btn)
print(f"My Army 'Attack!' Button: shape {army_attack_btn.shape}, norm pos: (0.825, 0.897)")

# Individual Army Cards
# Valkyrie icon
valk_icon = img_my_army[int(h*0.300):int(h*0.440), int(w*0.440):int(w*0.515)]
cv2.imwrite("assets/army/valkyrie_icon.png", valk_icon)

# Earthquake Spell icon
earthquake_icon = img_my_army[int(h*0.520):int(h*0.655), int(w*0.440):int(w*0.515)]
cv2.imwrite("assets/army/earthquake_spell_icon.png", earthquake_icon)

# Log Launcher icon
log_launcher_icon = img_my_army[int(h*0.520):int(h*0.655), int(w*0.760):int(w*0.835)]
cv2.imwrite("assets/army/log_launcher_icon.png", log_launcher_icon)

# Heroes (AQ, Dragon Duke, GW, BK)
aq_hero = img_my_army[int(h*0.285):int(h*0.810), int(w*0.068):int(w*0.155)]
cv2.imwrite("assets/army/hero_archer_queen.png", aq_hero)

dd_hero = img_my_army[int(h*0.285):int(h*0.810), int(w*0.158):int(w*0.245)]
cv2.imwrite("assets/army/hero_dragon_duke.png", dd_hero)

gw_hero = img_my_army[int(h*0.285):int(h*0.810), int(w*0.248):int(w*0.335)]
cv2.imwrite("assets/army/hero_grand_warden.png", gw_hero)

bk_hero = img_my_army[int(h*0.285):int(h*0.810), int(w*0.338):int(w*0.425)]
cv2.imwrite("assets/army/hero_barbarian_king.png", bk_hero)

# "My Army" header text
my_army_header = img_my_army[int(h*0.110):int(h*0.170), int(w*0.180):int(w*0.290)]
cv2.imwrite("assets/ui/my_army_header.png", my_army_header)

# --- 4. CLOUDS (SEARCHING FOR OPPONENTS) CROPS ---
h, w, _ = img_clouds.shape
# "Searching for opponents..." text & magnifying glass in center
searching_text = img_clouds[int(h*0.410):int(h*0.580), int(w*0.350):int(w*0.650)]
cv2.imwrite("assets/ui/searching_opponents_center.png", searching_text)

# "Return Home" button in bottom left
clouds_return_home = img_clouds[int(h*0.835):int(h*0.985), int(w*0.010):int(w*0.100)]
cv2.imwrite("assets/ui/clouds_return_home_button.png", clouds_return_home)

print("All templates successfully extracted and saved!")
