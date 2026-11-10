"""
Unit and Integration Tests for OCR & Vision Detectors.
Uses synthetic canvas rendering to verify text/digit recognition and image preprocessing.
"""

import unittest
import cv2
import numpy as np
from src.vision.ocr_engine import OCREngine
from src.vision.loot_detector import LootDetector
from src.vision.battle_detector import BattleDetector
from src.vision.state_detector import UIStateDetector
from src.state.game_state import UIState


class TestVisionAndOCR(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ocr = OCREngine()

    def test_digit_ocr_clean_image(self):
        # Create 100x300 canvas with white digits "1500000" on dark background
        img = np.zeros((100, 300, 3), dtype=np.uint8)
        cv2.putText(img, "1500000", (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)

        val, conf = self.ocr.read_integer(img)
        self.assertIsNotNone(val)
        self.assertEqual(val, 1500000)
        self.assertGreater(conf, 0.5)

    def test_timer_ocr(self):
        img = np.zeros((80, 200, 3), dtype=np.uint8)
        cv2.putText(img, "2m 45s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        secs, conf = self.ocr.read_timer(img)
        self.assertIsNotNone(secs)
        self.assertEqual(secs, 165)  # 2 * 60 + 45 = 165s

    def test_percentage_ocr(self):
        img = np.zeros((80, 200, 3), dtype=np.uint8)
        cv2.putText(img, "54%", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

        pct, conf = self.ocr.read_percentage(img)
        self.assertIsNotNone(pct)
        self.assertAlmostEqual(pct, 54.0, delta=1.0)

    def test_state_detector_candidate(self):
        # Full 1920x1080 canvas with "Next" in bottom-right
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(frame, "Next", (1700, 950), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 3)

        detector = UIStateDetector(self.ocr)
        res = detector.detect_ui_state(frame)
        self.assertEqual(res.value, UIState.CANDIDATE_BATTLE)

    def test_state_detector_home(self):
        # Full 1920x1080 canvas with "Attack" in bottom-left
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(frame, "Attack", (80, 950), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

        detector = UIStateDetector(self.ocr)
        res = detector.detect_ui_state(frame)
        self.assertEqual(res.value, UIState.HOME)


if __name__ == "__main__":
    unittest.main()
