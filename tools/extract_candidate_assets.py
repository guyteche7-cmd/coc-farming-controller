import os
import cv2
import numpy as np

img_candidate = cv2.imread(r"assets/reference/media_1787423558078.jpg")
img_clouds_transition = cv2.imread(r"assets/reference/media_1787423708404.png")

h, w, _ = img_candidate.shape
print(f"Candidate screen shape: {w}x{h}")

# Save full reference screens
cv2.imwrite("assets/test_cases/screen_5_candidate_enemy.png", img_candidate)
cv2.imwrite("assets/test_cases/screen_6_clouds_transition.png", img_clouds_transition)

# 1. "Next" Button (Bottom-Right: x: 875 to 1015, y: 405 to 455 in 1024x575)
next_btn = img_candidate[int(h*0.705):int(h*0.795), int(w*0.855):int(w*0.992)]
cv2.imwrite("assets/ui/next_button.png", next_btn)
print(f"Next Button: shape {next_btn.shape}, norm center: ({(0.855+0.992)/2:.3f}, {(0.705+0.795)/2:.3f})")

# 2. "End Battle" Button (Bottom-Left: x: 10 to 110, y: 420 to 455 in 1024x575)
end_battle_btn = img_candidate[int(h*0.730):int(h*0.795), int(w*0.010):int(w*0.110)]
cv2.imwrite("assets/ui/end_battle_button.png", end_battle_btn)
print(f"End Battle Button: shape {end_battle_btn.shape}, norm center: ({(0.010+0.110)/2:.3f}, {(0.730+0.795)/2:.3f})")

# 3. Available Loot Panel (Top-Left: x: 15 to 150, y: 45 to 135)
loot_panel = img_candidate[int(h*0.075):int(h*0.240), int(w*0.015):int(w*0.150)]
cv2.imwrite("assets/ui/loot_panel.png", loot_panel)

# Gold, Elixir, Dark Elixir specific rows
gold_row = img_candidate[int(h*0.105):int(h*0.150), int(w*0.040):int(w*0.145)]
elixir_row = img_candidate[int(h*0.150):int(h*0.195), int(w*0.040):int(w*0.145)]
de_row = img_candidate[int(h*0.195):int(h*0.240), int(w*0.040):int(w*0.145)]
cv2.imwrite("assets/ui/loot_gold_row.png", gold_row)
cv2.imwrite("assets/ui/loot_elixir_row.png", elixir_row)
cv2.imwrite("assets/ui/loot_dark_elixir_row.png", de_row)

# 4. "Battle starts in" header
battle_starts_in = img_candidate[int(h*0.005):int(h*0.080), int(w*0.440):int(w*0.560)]
cv2.imwrite("assets/ui/battle_starts_in_timer.png", battle_starts_in)

# 5. Army Deployment Ribbon Slots (Bottom ribbon: y: 470 to 565, x: 145 to 615)
ribbon_full = img_candidate[int(h*0.820):int(h*0.985), int(w*0.140):int(w*0.620)]
cv2.imwrite("assets/ui/candidate_army_ribbon.png", ribbon_full)

# Individual deployment slots from ribbon:
# Slot 0: Valkyrie x44 (x: 145 to 205)
slot_valk = img_candidate[int(h*0.825):int(h*0.980), int(w*0.142):int(w*0.205)]
cv2.imwrite("assets/army/deploy_slot_0_valkyrie.png", slot_valk)

# Slot 1: Log Launcher (x: 210 to 270)
slot_siege = img_candidate[int(h*0.825):int(h*0.980), int(w*0.208):int(w*0.272)]
cv2.imwrite("assets/army/deploy_slot_1_log_launcher.png", slot_siege)

# Slot 2: Archer Queen (x: 275 to 335)
slot_aq = img_candidate[int(h*0.825):int(h*0.980), int(w*0.275):int(w*0.338)]
cv2.imwrite("assets/army/deploy_slot_2_archer_queen.png", slot_aq)

# Slot 3: Dragon Duke (x: 340 to 400)
slot_dd = img_candidate[int(h*0.825):int(h*0.980), int(w*0.342):int(w*0.405)]
cv2.imwrite("assets/army/deploy_slot_3_dragon_duke.png", slot_dd)

# Slot 4: Grand Warden (x: 405 to 468)
slot_gw = img_candidate[int(h*0.825):int(h*0.980), int(w*0.408):int(w*0.472)]
cv2.imwrite("assets/army/deploy_slot_4_grand_warden.png", slot_gw)

# Slot 5: Barbarian King (x: 472 to 535)
slot_bk = img_candidate[int(h*0.825):int(h*0.980), int(w*0.475):int(w*0.538)]
cv2.imwrite("assets/army/deploy_slot_5_barbarian_king.png", slot_bk)

# Slot 6: Earthquake Spell x11 (x: 540 to 605)
slot_eq = img_candidate[int(h*0.825):int(h*0.980), int(w*0.542):int(w*0.605)]
cv2.imwrite("assets/army/deploy_slot_6_earthquake_spell.png", slot_eq)

print("Extracted all 7 deployment slots and candidate UI controls!")
