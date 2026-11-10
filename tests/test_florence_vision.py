"""
Tests for Level-3 Open-Vocabulary Vision & Florence-2 Popup Handling Engine.
Verifies zero-shot visual grounding, safe popup dismissal, and dangerous prompt protection.
"""

import unittest
import numpy as np
import cv2

from src.vision.florence_engine import Florence2VisionEngine, PopupDetection
from src.vision.state_detector import UIStateDetector
from src.state.game_state import UIState


class TestFlorenceVision(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize Florence engine with grounding fallback (fast, non-blocking)
        cls.engine = Florence2VisionEngine(auto_load_model=False)

    def test_safe_reload_popup_detection(self):
        """Simulate a 'Client and Server out of sync / Reload Game' modal dialog."""
        frame = np.full((1080, 1920, 3), 40, dtype=np.uint8)  # Dimmed background
        # Draw dialog box in center
        cv2.rectangle(frame, (500, 300), (1420, 780), (70, 70, 70), -1)
        cv2.putText(frame, "Connection Lost", (680, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
        cv2.putText(frame, "Client and server out of sync!", (620, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
        # Reload Game button
        cv2.rectangle(frame, (800, 600), (1120, 680), (0, 180, 0), -1)
        cv2.putText(frame, "Reload Game", (830, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        popup = self.engine.detect_popup(frame)
        self.assertIsNotNone(popup)
        self.assertEqual(popup.popup_type, "POPUP_RELOAD_SYNC")
        self.assertFalse(popup.is_dangerous)
        self.assertIsNotNone(popup.dismiss_point)
        # Dismiss point should land inside the Reload Game button
        self.assertAlmostEqual(popup.dismiss_point[0], 960 / 1920.0, delta=0.10)
        self.assertAlmostEqual(popup.dismiss_point[1], 640 / 1080.0, delta=0.10)

    def test_dangerous_gem_confirm_popup_blocked(self):
        """Simulate a dangerous prompt asking to spend Gems ('Spend 250 Gems to finish building now?')."""
        frame = np.full((1080, 1920, 3), 40, dtype=np.uint8)
        # Draw modal box
        cv2.rectangle(frame, (500, 300), (1420, 780), (60, 60, 60), -1)
        cv2.putText(frame, "Finish Upgrade Now?", (680, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
        cv2.putText(frame, "Spend 250 Gems to complete instantly", (580, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
        # Cancel button
        cv2.rectangle(frame, (650, 600), (900, 680), (100, 100, 100), -1)
        cv2.putText(frame, "Cancel", (720, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        # Confirm / Spend Gems button
        cv2.rectangle(frame, (1000, 600), (1250, 680), (0, 180, 0), -1)
        cv2.putText(frame, "Spend Gems", (1030, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        popup = self.engine.detect_popup(frame)
        self.assertIsNotNone(popup)
        self.assertEqual(popup.popup_type, "POPUP_GEM_CONFIRM")
        self.assertTrue(popup.is_dangerous)
        # Dismiss type should target CANCEL to protect user's gems
        self.assertEqual(popup.dismiss_type, "CANCEL")

    def test_state_detector_integration_with_popup(self):
        """Verify UIStateDetector detects POPUP_MODAL and sets dynamic anchor."""
        frame = np.full((1080, 1920, 3), 40, dtype=np.uint8)
        cv2.rectangle(frame, (500, 300), (1420, 780), (70, 70, 70), -1)
        cv2.putText(frame, "Notice", (900, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
        cv2.putText(frame, "Personal break limit reached!", (650, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
        cv2.rectangle(frame, (850, 600), (1070, 680), (0, 180, 0), -1)
        cv2.putText(frame, "Okay", (920, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        detector = UIStateDetector()
        res = detector.detect_ui_state(frame)
        self.assertEqual(res.value, UIState.POPUP_MODAL)
        self.assertIsNotNone(detector.last_popup)
        self.assertEqual(detector.last_popup.popup_type, "POPUP_PERSONAL_BREAK")
        self.assertIn("POPUP_DISMISS_BUTTON", detector.dynamic_anchors)


if __name__ == "__main__":
    unittest.main()
