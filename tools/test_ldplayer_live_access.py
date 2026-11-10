import sys
import os
import cv2
import time

sys.path.insert(0, os.path.abspath("."))

from src.calibration.viewport import ViewportCalibrator
from src.capture.screen_capture import ScreenCapture
from src.vision.state_detector import UIStateDetector
from src.vision.loot_detector import LootDetector

print("=== ACCESSING LIVE GAME ON LDPLAYER ===")

calibrator = ViewportCalibrator(title_pattern="LDPlayer|Clash of Clans|Google Play Games|BlueStacks")
geom = calibrator.calibrate_live_window()

print(f"Connected Window Title: '{geom.window_title}'")
print(f"Window Handle (HWND): {geom.hwnd}")
print(f"Screen Geometry: {geom.window_width}x{geom.window_height} at ({geom.window_x}, {geom.window_y})")

if not geom.hwnd:
    print("❌ LDPlayer window not found! Please make sure LDPlayer is open.")
    sys.exit(1)

# Focus window
print("Bringing LDPlayer window to foreground...")
calibrator.focus_game_window()
time.sleep(0.5)

# Capture Live Frame
cap = ScreenCapture(calibrator)
frame = cap.capture_frame()

if frame is None or frame.size == 0:
    print("❌ Failed to capture frame from LDPlayer window.")
    sys.exit(1)

h, w, _ = frame.shape
print(f"Successfully captured live frame: {w}x{h}")

# Detect UI State
detector = UIStateDetector(use_ai=True)
state_res = detector.detect_ui_state(frame)
print(f"Active Game UI State: {state_res.value} ({state_res.confidence*100:.0f}% confidence)")
print("Dynamic Anchors Detected:", detector.dynamic_anchors)

# Read Loot if in candidate battle
if state_res.value.name in ("CANDIDATE_BATTLE", "UNKNOWN"):
    loot_det = LootDetector()
    loot_res = loot_det.detect_candidate_loot(frame)
    print(f"Detected Available Loot: Gold={loot_res.value.gold:,}, Elixir={loot_res.value.elixir:,}, DE={loot_res.value.dark_elixir:,}")

# Annotate and save diagnostic preview
vis = frame.copy()
cv2.rectangle(vis, (10, 10), (min(w-10, 580), 55), (0, 0, 0), -1)
cv2.putText(vis, f"LDPLAYER LIVE: {state_res.value}", (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)

os.makedirs("data/diagnostics", exist_ok=True)
out_path = "data/diagnostics/ldplayer_live_access.png"
cv2.imwrite(out_path, vis)
print(f"\nSaved live visual snapshot to: {out_path}")
print("==========================================")
print("SUCCESS: LIVE ACCESS TO LDPLAYER CONFIRMED AND WORKING!")
print("==========================================")
