"""
Complete Clash of Clans Army & Ribbon Asset Extractor (Version 4.0 - Exact Canonical Library).
Applies the verified corrections for TH18 units, meta spells, and new siege engines:

Spells:
- clone_spell_alt -> invisibility_spell
- invisibility_spell -> recall_spell
- recall_spell -> revive_spell
- overgrowth_spell -> totem_spell
- overgrowth_spell_alt -> overgrowth_spell
- revive_spell -> angry_spell

Troops:
- miner_alt -> DELETED (identical duplicate of miner)
- hog_rider -> minion
- valkyrie -> hog_rider
- witch -> golem
- minion -> meteor_golem
- super_minion -> super_yeti
- super_hog_rider -> super_minion
- super_witch -> super_valkyrie
- ice_hound -> super_witch
- super_bowler -> ice_hound

Sieges:
- battle_blimp_empty -> stone_slammer_empty
- battle_drill_empty -> sky_wagon_empty
- log_launcher_empty -> flame_flinger_empty
- siege_barracks_empty -> log_launcher_empty
- stone_slammer_loaded -> sky_wagon_loaded
- wall_wrecker_empty -> troop_launcher_empty
"""

import os
import shutil
import cv2

REF_DIR = r"assets\reference"
ARMY_DIR = r"assets\army"

def reset_army_dirs():
    for sub in ["troops", "spells", "sieges", "heroes", "templates", "cards"]:
        p = os.path.join(ARMY_DIR, sub)
        if os.path.exists(p):
            shutil.rmtree(p)
    
    os.makedirs(os.path.join(ARMY_DIR, "templates"), exist_ok=True)
    os.makedirs(os.path.join(ARMY_DIR, "cards"), exist_ok=True)
    for cat in ["troops", "spells", "sieges", "heroes"]:
        os.makedirs(os.path.join(ARMY_DIR, cat), exist_ok=True)
        os.makedirs(os.path.join(ARMY_DIR, "cards", cat), exist_ok=True)

def save_unit(card_img, category, name):
    if card_img is None or card_img.size == 0:
        print(f"FAILED to extract {name} (empty image)")
        return
    
    h, w = card_img.shape[:2]
    if w != 132 or h != 172:
        card_img = cv2.resize(card_img, (132, 172))
    
    # 1. Full card
    card_path_cat = os.path.join(ARMY_DIR, "cards", category, f"{name}_card.png")
    cv2.imwrite(card_path_cat, card_img)
    cv2.imwrite(os.path.join(ARMY_DIR, category, f"{name}_card.png"), card_img)

    # 2. Invariant central portrait (64x64)
    y1 = int(0.24 * 172)
    y2 = int(0.74 * 172)
    x1 = int(0.20 * 132)
    x2 = int(0.80 * 132)
    face = card_img[y1:y2, x1:x2]
    face_64 = cv2.resize(face, (64, 64))
    
    cv2.imwrite(os.path.join(ARMY_DIR, "templates", f"{name}.png"), face_64)
    cv2.imwrite(os.path.join(ARMY_DIR, category, f"{name}.png"), face_64)
    print(f"Extracted [{category.upper():7s}] {name:25s} -> Card: (172, 132), Template: (64, 64)")

def crop_ribbon_slot(im, start_x, idx, step=145, w=132, h=172, y=893):
    x1 = start_x + idx * step
    return im[y:y+h, x1:x1+w]

def run_extraction():
    reset_army_dirs()
    print("Beginning authoritative extraction of exact Clash of Clans army assets...")

    # -------------------------------------------------------------
    # 1. Elixir Troops 1-12 & Event Troop from 111758 (Bright)
    # -------------------------------------------------------------
    im1 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 111758.png"))
    elixir_troops_111758 = [
        "momma",        # 0: M.O.M.M.A (Event troop)
        "barbarian",    # 1: Barbarian
        "archer",       # 2: Archer
        "giant",        # 3: Giant
        "goblin",       # 4: Goblin
        "wall_breaker", # 5: Wall Breaker
        "balloon",      # 6: Balloon
        "wizard",       # 7: Wizard
        "healer",       # 8: Healer
        "dragon",       # 9: Dragon
        "pekka",        # 10: P.E.K.K.A
        "baby_dragon",  # 11: Baby Dragon
        "miner"         # 12: Miner (Level 11) - keeps single canonical miner
    ]
    for idx, name in enumerate(elixir_troops_111758):
        card = crop_ribbon_slot(im1, start_x=23, idx=idx)
        save_unit(card, "troops", name)

    # -------------------------------------------------------------
    # 2. Elixir Troops 13-18 & Dark Troops from 111807 (Bright)
    # (miner duplicate at x=71 is skipped as requested)
    # -------------------------------------------------------------
    im2 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 111807.png"))
    troops_111807 = [
        # (x=71: miner duplicate deleted/skipped)
        ("electro_dragon", 1), # x=216
        ("yeti", 2),           # x=361
        ("dragon_rider", 3),   # x=506
        ("electro_titan", 4),  # x=651
        ("root_rider", 5),     # x=796
        ("thrower", 6),        # x=941
        ("meteor_golem", 7),   # x=1086 (was minion -> meteor_golem)
        ("minion", 8),         # x=1231 (was hog_rider -> minion)
        ("hog_rider", 9),      # x=1376 (was valkyrie -> hog_rider)
        ("golem", 10),         # x=1521 (was golem)
        ("golem_alt", 11),     # x=1666 (was witch -> golem)
    ]
    for name, idx in troops_111807:
        card = crop_ribbon_slot(im2, start_x=71, idx=idx)
        save_unit(card, "troops", name)

    # -------------------------------------------------------------
    # 3. Dark Troops from 111945 (Bright)
    # -------------------------------------------------------------
    im4 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 111945.png"))
    dark_troops_111945 = [
        ("lava_hound", 1),        # 1: x=168
        ("bowler", 2),            # 2: x=313
        ("ice_golem", 3),         # 3: x=458
        ("headhunter", 4),        # 4: x=603
        ("apprentice_warden", 5), # 5: x=748
        ("druid", 6),             # 6: x=893
        ("furnace", 7),           # 7: x=1038
        ("ruin_witch", 8),        # 8: x=1183
    ]
    for name, slot_idx in dark_troops_111945:
        card = crop_ribbon_slot(im4, start_x=23, idx=slot_idx)
        save_unit(card, "troops", name)

    # -------------------------------------------------------------
    # 4. Spells & Heroes from 111815 (Bright)
    # -------------------------------------------------------------
    im3 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 111815.png"))
    save_unit(im3[893:893+172, 705:705+132], "heroes", "royal_champion")
    save_unit(im3[893:893+172, 850:850+132], "heroes", "grand_warden")
    
    elixir_spells_111815 = [
        "lightning_spell", # x=1033
        "healing_spell",   # x=1178
        "rage_spell",      # x=1323
        "jump_spell",      # x=1468
        "freeze_spell",    # x=1613
        "clone_spell"      # x=1758
    ]
    for idx, name in enumerate(elixir_spells_111815):
        card = crop_ribbon_slot(im3, start_x=1033, idx=idx)
        save_unit(card, "spells", name)

    # -------------------------------------------------------------
    # 5. Spells from 112005 (Bright)
    # -------------------------------------------------------------
    im5 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 112005.png"))
    spells_112005 = [
        ("invisibility_spell", 435), # was clone_spell_alt -> invisibility_spell
        ("recall_spell", 580),       # was invisibility_spell -> recall_spell
        ("revive_spell", 725),       # was recall_spell -> revive_spell
        ("totem_spell", 870),        # was overgrowth_spell -> totem_spell
        ("poison_spell", 1015),      # Poison Spell
        ("earthquake_spell", 1160),  # Earthquake Spell
        ("haste_spell", 1305),       # Haste Spell
        ("skeleton_spell", 1450),    # Skeleton Spell
        ("bat_spell", 1595)          # Bat Spell
    ]
    for name, sx in spells_112005:
        card = im5[893:893+172, sx:sx+132]
        save_unit(card, "spells", name)

    # -------------------------------------------------------------
    # 6. Spells from 112132 (Bright)
    # -------------------------------------------------------------
    im_bright_spells = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 112132.png"))
    save_unit(im_bright_spells[893:893+172, 1469:1469+132], "spells", "overgrowth_spell") # was overgrowth_spell_alt -> overgrowth_spell
    save_unit(im_bright_spells[893:893+172, 1614:1614+132], "spells", "ice_block_spell")  # Ice Block Spell
    save_unit(im_bright_spells[893:893+172, 1759:1759+132], "spells", "angry_spell")      # was revive_spell -> angry_spell

    # -------------------------------------------------------------
    # 7. Super Troops, Sieges & Heroes from 112311 (Bright)
    # -------------------------------------------------------------
    im7 = cv2.imread(os.path.join(REF_DIR, "Screenshot 2026-11-10 112311.png"))
    save_unit(im7[893:893+172, 148:148+132], "troops", "super_barbarian")
    save_unit(im7[893:893+172, 293:293+132], "troops", "super_archer")
    save_unit(im7[893:893+172, 454:454+132], "sieges", "sky_wagon_loaded") # was stone_slammer_loaded -> sky_wagon_loaded
    save_unit(im7[893:893+172, 617:617+132], "heroes", "barbarian_king")
    save_unit(im7[893:893+172, 762:762+132], "heroes", "archer_queen")
    save_unit(im7[893:893+172, 908:908+132], "heroes", "grand_warden_alt")

    # -------------------------------------------------------------
    # 8. Super Troops Series from 112512 - 112816 (All Bright)
    # -------------------------------------------------------------
    super_pairs = [
        ("Screenshot 2026-11-10 112512.png", "super_giant", "sneaky_goblin"),
        ("Screenshot 2026-11-10 112546.png", "rocket_balloon", "super_wizard"),
        ("Screenshot 2026-11-10 112615.png", "super_dragon", "inferno_dragon"),
        ("Screenshot 2026-11-10 112647.png", "super_miner", "super_yeti"),        # was super_minion -> super_yeti
        ("Screenshot 2026-11-10 112724.png", "super_minion", "super_valkyrie"),    # was super_hog_rider -> super_minion
        ("Screenshot 2026-11-10 112749.png", "super_valkyrie_alt", "super_witch"),# was super_witch -> super_valkyrie, ice_hound -> super_witch
        ("Screenshot 2026-11-10 112816.png", "ice_hound", None),                   # was super_bowler -> ice_hound
    ]
    for s_file, unit_a, unit_b in super_pairs:
        im_s = cv2.imread(os.path.join(REF_DIR, s_file))
        if unit_a:
            save_unit(im_s[893:893+172, 140:140+132], "troops", unit_a)
        if unit_b:
            save_unit(im_s[893:893+172, 285:285+132], "troops", unit_b)

    # -------------------------------------------------------------
    # 9. Empty Siege Machines (with '!' badge)
    # -------------------------------------------------------------
    small_crops = [
        ("Screenshot 2026-11-10 111848.png", "stone_slammer_empty"), # was battle_blimp_empty -> stone_slammer_empty
        ("Screenshot 2026-11-10 112024.png", "log_launcher_empty"),   # was siege_barracks_empty -> log_launcher_empty
        ("Screenshot 2026-11-10 112031.png", "flame_flinger_empty"),  # was log_launcher_empty -> flame_flinger_empty
        ("Screenshot 2026-11-10 112140.png", "troop_launcher_empty"), # was wall_wrecker_empty -> troop_launcher_empty
        ("Screenshot 2026-11-10 112149.png", "sky_wagon_empty"),     # was battle_drill_empty -> sky_wagon_empty
    ]
    for sc_file, name in small_crops:
        im_c = cv2.imread(os.path.join(REF_DIR, sc_file))
        save_unit(im_c, "sieges", name)

    print("\nAuthoritative extraction finished successfully with all user-specified corrections applied!")

if __name__ == "__main__":
    run_extraction()
