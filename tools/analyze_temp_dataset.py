import os
import glob
import cv2
import sys
sys.path.insert(0, os.path.abspath("."))

from src.vision.state_detector import UIStateDetector
from src.vision.loot_detector import LootDetector
from src.planning.deployment_planner import DeploymentPlanner

temp_dir = r"temp"
img_paths = glob.glob(os.path.join(temp_dir, "*.png")) + glob.glob(os.path.join(temp_dir, "*.jpg"))

print(f"Found {len(img_paths)} dataset images in temp/\n")

detector = UIStateDetector(use_ai=True)
loot_detector = LootDetector()
planner = DeploymentPlanner(edge="top")

results = []

for idx, pth in enumerate(sorted(img_paths)):
    fname = os.path.basename(pth)
    img = cv2.imread(pth)
    if img is None:
        continue
    h, w, _ = img.shape
    
    # Detect State
    state_res = detector.detect_ui_state(img)
    
    # Read Loot
    loot_res = loot_detector.detect_candidate_loot(img)
    g, e, de = loot_res.value.gold, loot_res.value.elixir, loot_res.value.dark_elixir
    
    # AI Detections summary
    ai_count = sum(len(items) for items in detector.last_ai_detections.values()) if detector.last_ai_detections else 0
    ai_classes = list(detector.last_ai_detections.keys()) if detector.last_ai_detections else []

    # Verify top deployment line coordinates: check if (px, py) lands on outer grass
    line_pts = planner._generate_line_points(5)
    outside_check = True
    for norm_x, norm_y in line_pts:
        px = int(norm_x * w)
        py = int(norm_y * h)
        # Verify point is within image bounds
        if px < 0 or px >= w or py < 0 or py >= h:
            outside_check = False

    print(f"[{idx+1:02d}/{len(img_paths)}] {fname[:32]:32s} | Size: {w}x{h} | State: {state_res.value:18s} ({state_res.confidence*100:.0f}%) | Loot: G={g:,} E={e:,} DE={de:,} | AI Dets: {ai_count} ({ai_classes})")

print("\nDataset Batch Analysis Completed!")
