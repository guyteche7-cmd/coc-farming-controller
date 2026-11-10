"""
Extracts and indexes all troop, spell, siege machine, and hero icons from reference screenshots.
Saves both the full card and the clean invariant central template (excluding level, pet, and count badges).
"""

import os
import cv2
import numpy as np

REF_DIR = r"temp\ref"
ARMY_DIR = r"assets\army"

def save_asset(card_img, category, name):
    cat_dir = os.path.join(ARMY_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    
    # 1. Full card
    card_path = os.path.join(cat_dir, f"{name}_card.png")
    cv2.imwrite(card_path, card_img)
    
    # 2. Invariant core template (central portrait):
    # Ignore top badge (0-25% y), bottom level (75-100% y), left pet icon (0-35% y, 0-40% x)
    # A 64x64 or 70x70 crop centered on the face/bottle
    h, w = card_img.shape[:2]
    # Center face region: y: 22% to 75%, x: 18% to 82%
    y1 = int(0.22 * h)
    y2 = int(0.75 * h)
    x1 = int(0.18 * w)
    x2 = int(0.82 * w)
    face = card_img[y1:y2, x1:x2]
    
    tmpl_path = os.path.join(cat_dir, f"{name}.png")
    cv2.imwrite(tmpl_path, face)
    print(f"Saved [{category}] {name}: card={card_img.shape}, tmpl={face.shape}")

def extract_from_ribbon(img_name, slot_coords_dict):
    path = os.path.join(REF_DIR, img_name)
    im = cv2.imread(path)
    if im is None:
        print(f"Error loading {path}")
        return
    for (category, name), (x1, y1, w, h) in slot_coords_dict.items():
        card = im[y1:y1+h, x1:x1+w]
        save_asset(card, category, name)

if __name__ == "__main__":
    print("Starting asset extraction...")
