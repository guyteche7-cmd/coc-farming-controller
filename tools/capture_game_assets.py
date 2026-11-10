"""
Asset Capture and Screen Calibration Tool.
Captures live screenshots from the active game window, automatically extracts
standard UI templates (Next button, Attack button, End Battle button, Loot Panel),
and saves them into assets/ for 100x faster template matching.
"""

from __future__ import annotations
import os
import sys
import time
import argparse
import logging
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.calibration.viewport import ViewportCalibrator
from src.capture.screen_capture import ScreenCapture

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AssetCapture")


def extract_standard_templates(full_frame: np.ndarray, base_dir: str = "assets/ui") -> None:
    """Extracts standard UI crops based on 1920x1080 normalized coordinates."""
    os.makedirs(base_dir, exist_ok=True)
    h, w, _ = full_frame.shape
    logger.info(f"Extracting templates from frame resolution: {w}x{h}")

    # Standard UI regions for 1920x1080
    templates_map = {
        "next_button": (int(h * 0.82), int(h * 0.96), int(w * 0.86), int(w * 0.98)),
        "attack_button": (int(h * 0.82), int(h * 0.98), int(w * 0.02), int(w * 0.12)),
        "end_battle_button": (int(h * 0.72), int(h * 0.85), int(w * 0.02), int(w * 0.12)),
        "return_home_button": (int(h * 0.82), int(h * 0.96), int(w * 0.42), int(w * 0.58)),
        "loot_panel": (int(h * 0.06), int(h * 0.28), int(w * 0.03), int(w * 0.24)),
        "army_ribbon": (int(h * 0.85), int(h * 0.99), int(w * 0.05), int(w * 0.85))
    }

    for name, (y1, y2, x1, x2) in templates_map.items():
        crop = full_frame[y1:y2, x1:x2]
        if crop.size > 0:
            save_path = os.path.join(base_dir, f"{name}.png")
            cv2.imwrite(save_path, crop)
            logger.info(f"Saved template '{name}' ({crop.shape[1]}x{crop.shape[0]}) to {save_path}")


def capture_live(calibrator: ViewportCalibrator, capture: ScreenCapture) -> None:
    calibrator.calibrate_live_window()
    calibrator.focus_game_window()
    time.sleep(0.5)

    frame = capture.capture_frame()
    if frame is None or frame.size == 0:
        logger.error("Failed to capture frame from game window.")
        return

    # Save full screenshot
    ts = time.strftime("%Y%m%d_%H%M%S")
    full_path = f"assets/test_cases/capture_{ts}.png"
    os.makedirs("assets/test_cases", exist_ok=True)
    cv2.imwrite(full_path, frame)
    logger.info(f"Captured live screen -> {full_path}")

    # Extract templates
    extract_standard_templates(frame)
    logger.info("Template extraction complete! Visual recognition is now primed.")


def main():
    parser = argparse.ArgumentParser(description="CoC Asset & Screen Capture Tool")
    parser.add_argument("--import-file", type=str, help="Import an existing screenshot file and generate templates")
    parser.add_argument("--output-dir", type=str, default="assets/ui", help="Directory to save extracted templates")
    args = parser.parse_args()

    if args.import_file and os.path.exists(args.import_file):
        img = cv2.imread(args.import_file)
        if img is not None:
            extract_standard_templates(img, base_dir=args.output_dir)
            logger.info(f"Templates imported from {args.import_file}")
            return
        else:
            logger.error(f"Could not load image: {args.import_file}")
            return

    calibrator = ViewportCalibrator()
    capture = ScreenCapture(calibrator)
    capture_live(calibrator, capture)


if __name__ == "__main__":
    main()
