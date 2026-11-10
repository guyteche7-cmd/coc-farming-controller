import os
import cv2

img = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787428724348.png")
h, w, _ = img.shape
print(f"My Army Screen resolution: {w}x{h}")

os.makedirs("assets/army", exist_ok=True)
os.makedirs("assets/ui", exist_ok=True)

# 1. Green "Attack!" button on bottom right of modal
# Box roughly: x: 75% to 92%, y: 82% to 89%
attack_btn = img[int(h*0.82):int(h*0.89), int(w*0.75):int(w*0.92)]
cv2.imwrite("assets/ui/army_screen_attack_button.png", attack_btn)

# 2. Valkyrie Troop Icon (x40)
# Troop section is upper right box
valk_crop = img[int(h*0.29):int(h*0.42), int(w*0.44):int(w*0.51)]
cv2.imwrite("assets/army/valkyrie_icon.png", valk_crop)

# 3. Earthquake Spell Icon (x11)
spell_crop = img[int(h*0.52):int(h*0.65), int(w*0.44):int(w*0.51)]
cv2.imwrite("assets/army/earthquake_spell_icon.png", spell_crop)

# 4. Log Launcher Siege Machine Icon (x3)
siege_crop = img[int(h*0.52):int(h*0.65), int(w*0.76):int(w*0.83)]
cv2.imwrite("assets/army/log_launcher_icon.png", siege_crop)

# 5. Hero Cards
# Hero 1: Minion Prince / Dragon Duke (Slot 0)
h1_crop = img[int(h*0.28):int(h*0.73), int(w*0.09):int(w*0.17)]
cv2.imwrite("assets/army/hero_minion_prince.png", h1_crop)

# Hero 2: Archer Queen (Slot 1)
h2_crop = img[int(h*0.28):int(h*0.73), int(w*0.17):int(w*0.25)]
cv2.imwrite("assets/army/hero_archer_queen.png", h2_crop)

# Hero 3: Grand Warden (Slot 2)
h3_crop = img[int(h*0.28):int(h*0.73), int(w*0.25):int(w*0.33)]
cv2.imwrite("assets/army/hero_grand_warden.png", h3_crop)

# Hero 4: Barbarian King (Slot 3)
h4_crop = img[int(h*0.28):int(h*0.73), int(w*0.33):int(w*0.42)]
cv2.imwrite("assets/army/hero_barbarian_king.png", h4_crop)

print("Extracted all Army composition assets from screenshot!")
