import os
import glob
import cv2
import numpy as np

asset_dir = "assets/ui"
asset_files = sorted(glob.glob(os.path.join(asset_dir, "*.png")))

print(f"Auditing {len(asset_files)} UI asset templates...\n")

invalid_assets = []
good_assets = []

for fpath in asset_files:
    fname = os.path.basename(fpath)
    img = cv2.imread(fpath)
    if img is None:
        print(f"[CORRUPT FILE] {fname}: Unable to read image!")
        invalid_assets.append((fname, "Corrupt file"))
        continue
        
    h, w, c = img.shape
    mean_val = img.mean()
    std_val = img.std()
    
    # Check for near-blank/solid color crops (std < 12) or weird crops
    if std_val < 12.0:
        print(f"[LOW VARIANCE / BLANK] {fname}: Size {w}x{h}, Mean={mean_val:.1f}, Std={std_val:.1f}")
        invalid_assets.append((fname, f"Blank/Solid color crop (Std={std_val:.1f})"))
    elif w < 10 or h < 10:
        print(f"[TOO SMALL] {fname}: Size {w}x{h}")
        invalid_assets.append((fname, f"Too small ({w}x{h})"))
    else:
        good_assets.append(fname)
        print(f"[OK] {fname:32s}: Size {w}x{h}, Std={std_val:.1f}")

print("\n--- Summary ---")
print(f"Total Assets: {len(asset_files)}")
print(f"Good Assets:  {len(good_assets)}")
print(f"Invalid/Bad Assets: {len(invalid_assets)}")
for name, reason in invalid_assets:
    print(f"  - {name}: {reason}")
