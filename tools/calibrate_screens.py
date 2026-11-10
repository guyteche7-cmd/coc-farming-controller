"""
Multi-Screen Interactive Asset Calibration Studio.
Allows capturing each distinct game screen (Home, Candidate, In-Battle, Results, Walls)
individually or via global hotkeys (F6-F12) to extract accurate UI templates.
"""

from __future__ import annotations
import os
import sys
import time
import logging
from typing import Dict, Tuple, Optional
import cv2
import numpy as np
import keyboard

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.calibration.viewport import ViewportCalibrator
from src.capture.screen_capture import ScreenCapture
from src.control.notifier import Notifier

logger = logging.getLogger("CalibrateScreens")


class ScreenAssetCalibrator:
    """Manages screen-by-screen template extraction."""

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self.calibrator = ViewportCalibrator()
        self.capture = ScreenCapture(self.calibrator)
        self.notifier = Notifier()
        os.makedirs(os.path.join(assets_dir, "ui"), exist_ok=True)
        os.makedirs(os.path.join(assets_dir, "test_cases"), exist_ok=True)

    def capture_current_frame(self) -> Optional[np.ndarray]:
        self.calibrator.calibrate_live_window()
        self.calibrator.focus_game_window()
        time.sleep(0.3)
        return self.capture.capture_frame()

    def process_home_screen(self, frame: Optional[np.ndarray] = None) -> Dict[str, str]:
        """Captures and crops elements from the Home Village screen."""
        if frame is None:
            frame = self.capture_current_frame()
        if frame is None:
            return {}

        h, w, _ = frame.shape
        # Save full frame
        full_path = os.path.join(self.assets_dir, "test_cases", "screen_home.png")
        cv2.imwrite(full_path, frame)

        # 1. Attack Button (Bottom-Left)
        attack_crop = frame[int(h * 0.82):int(h * 0.98), int(w * 0.015):int(w * 0.125)]
        p1 = os.path.join(self.assets_dir, "ui", "attack_button.png")
        cv2.imwrite(p1, attack_crop)

        # 2. Builder HUD (Top-Center)
        builder_crop = frame[int(h * 0.01):int(h * 0.08), int(w * 0.42):int(w * 0.58)]
        p2 = os.path.join(self.assets_dir, "ui", "builder_hud.png")
        cv2.imwrite(p2, builder_crop)

        # 3. Gold & Elixir Storages (Top-Right)
        storage_crop = frame[int(h * 0.01):int(h * 0.18), int(w * 0.74):int(w * 0.96)]
        p3 = os.path.join(self.assets_dir, "ui", "storage_hud.png")
        cv2.imwrite(p3, storage_crop)

        self.notifier.announce("Home Village screen calibrated successfully", chime="accept")
        return {"attack_button": p1, "builder_hud": p2, "storage_hud": p3, "full_screen": full_path}

    def process_candidate_screen(self, frame: Optional[np.ndarray] = None) -> Dict[str, str]:
        """Captures and crops elements from the Candidate Enemy Village screen."""
        if frame is None:
            frame = self.capture_current_frame()
        if frame is None:
            return {}

        h, w, _ = frame.shape
        full_path = os.path.join(self.assets_dir, "test_cases", "screen_candidate.png")
        cv2.imwrite(full_path, frame)

        # 1. Next Button (Bottom-Right)
        next_crop = frame[int(h * 0.82):int(h * 0.96), int(w * 0.86):int(w * 0.985)]
        p1 = os.path.join(self.assets_dir, "ui", "next_button.png")
        cv2.imwrite(p1, next_crop)

        # 2. Loot Panel (Top-Left)
        loot_crop = frame[int(h * 0.06):int(h * 0.28), int(w * 0.03):int(w * 0.24)]
        p2 = os.path.join(self.assets_dir, "ui", "loot_panel.png")
        cv2.imwrite(p2, loot_crop)

        # 3. End Battle Button in Candidate (Bottom-Left)
        end_crop = frame[int(h * 0.74):int(h * 0.86), int(w * 0.02):int(w * 0.13)]
        p3 = os.path.join(self.assets_dir, "ui", "end_battle_button.png")
        cv2.imwrite(p3, end_crop)

        self.notifier.announce("Candidate matchmaking screen calibrated", chime="accept")
        return {"next_button": p1, "loot_panel": p2, "end_battle_button": p3, "full_screen": full_path}

    def process_battle_screen(self, frame: Optional[np.ndarray] = None) -> Dict[str, str]:
        """Captures and crops elements from the In-Battle screen."""
        if frame is None:
            frame = self.capture_current_frame()
        if frame is None:
            return {}

        h, w, _ = frame.shape
        full_path = os.path.join(self.assets_dir, "test_cases", "screen_battle.png")
        cv2.imwrite(full_path, frame)

        # 1. Army Ribbon (Bottom Bar)
        ribbon_crop = frame[int(h * 0.85):int(h * 0.99), int(w * 0.05):int(w * 0.88)]
        p1 = os.path.join(self.assets_dir, "ui", "army_ribbon.png")
        cv2.imwrite(p1, ribbon_crop)

        # 2. Battle Timer & Damage (Top-Left)
        timer_crop = frame[int(h * 0.02):int(h * 0.18), int(w * 0.02):int(w * 0.18)]
        p2 = os.path.join(self.assets_dir, "ui", "battle_timer.png")
        cv2.imwrite(p2, timer_crop)

        # 3. Surrender Button (Bottom-Left)
        surrender_crop = frame[int(h * 0.74):int(h * 0.86), int(w * 0.02):int(w * 0.13)]
        p3 = os.path.join(self.assets_dir, "ui", "surrender_button.png")
        cv2.imwrite(p3, surrender_crop)

        self.notifier.announce("In battle screen and army ribbon calibrated", chime="accept")
        return {"army_ribbon": p1, "battle_timer": p2, "surrender_button": p3, "full_screen": full_path}

    def process_result_screen(self, frame: Optional[np.ndarray] = None) -> Dict[str, str]:
        """Captures and crops elements from the Victory/Defeat result screen."""
        if frame is None:
            frame = self.capture_current_frame()
        if frame is None:
            return {}

        h, w, _ = frame.shape
        full_path = os.path.join(self.assets_dir, "test_cases", "screen_results.png")
        cv2.imwrite(full_path, frame)

        # 1. Return Home Button (Bottom-Center)
        return_crop = frame[int(h * 0.82):int(h * 0.96), int(w * 0.42):int(w * 0.58)]
        p1 = os.path.join(self.assets_dir, "ui", "return_home_button.png")
        cv2.imwrite(p1, return_crop)

        self.notifier.announce("Battle result screen calibrated", chime="accept")
        return {"return_home_button": p1, "full_screen": full_path}

    def process_wall_screen(self, frame: Optional[np.ndarray] = None) -> Dict[str, str]:
        """Captures and crops elements from the Wall Selection modal."""
        if frame is None:
            frame = self.capture_current_frame()
        if frame is None:
            return {}

        h, w, _ = frame.shape
        full_path = os.path.join(self.assets_dir, "test_cases", "screen_walls.png")
        cv2.imwrite(full_path, frame)

        # Batch upgrade button (Bottom-Center modal)
        batch_crop = frame[int(h * 0.78):int(h * 0.94), int(w * 0.45):int(w * 0.65)]
        p1 = os.path.join(self.assets_dir, "ui", "wall_upgrade_modal.png")
        cv2.imwrite(p1, batch_crop)

        self.notifier.announce("Wall upgrade interface calibrated", chime="accept")
        return {"wall_upgrade_modal": p1, "full_screen": full_path}
