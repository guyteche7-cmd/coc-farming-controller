"""
Unit and Integration Tests for Tier 4 Multimodal Vision-Language Model (VLM Fallback) Engine.
Verifies multimodal schema validation, rate-limiting, dangerous prompt protection, and local VLM fallback.
"""

import unittest
import numpy as np
import cv2

from src.vision.vlm_engine import MultimodalVLMEngine, VLMReasoningResult, VLMActionType


class TestVLMEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize engine in local fallback mode (no network dependency during unit tests)
        cls.engine = MultimodalVLMEngine(enable_external=False)

    def test_vlm_reasoning_schema(self):
        """Verify Pydantic schema validation and field parsing."""
        data = {
            "scene_summary": "Test scene",
            "screen_classification": "MODAL_POPUP",
            "is_stuck_or_deadlocked": True,
            "is_dangerous": False,
            "suggested_action": "DISMISS_POPUP",
            "target_coordinates": [0.5, 0.6],
            "target_element_description": "Okay Button",
            "confidence": 0.95,
            "reasoning": "Simple test reasoning",
            "source_model": "test-vlm"
        }
        res = VLMReasoningResult.model_validate(data)
        self.assertEqual(res.suggested_action, VLMActionType.DISMISS_POPUP)
        self.assertEqual(list(res.target_coordinates), [0.5, 0.6])
        self.assertTrue(res.is_stuck_or_deadlocked)

    def test_vlm_dangerous_gem_protection(self):
        """Simulate an unexpected modal asking to spend 250 Gems."""
        frame = np.full((1080, 1920, 3), 40, dtype=np.uint8)
        cv2.rectangle(frame, (500, 300), (1420, 780), (60, 60, 60), -1)
        cv2.putText(frame, "Finish Building Upgrade?", (650, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, "Spend 250 Gems to finish now!", (600, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
        cv2.rectangle(frame, (700, 600), (950, 680), (80, 80, 80), -1)
        cv2.putText(frame, "Cancel", (770, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        res = self.engine.analyze_screen(frame, force=True)
        self.assertTrue(res.is_dangerous)
        self.assertEqual(res.suggested_action, VLMActionType.PAUSE)
        self.assertEqual(res.screen_classification, "GEM_SPEND_PROMPT")

    def test_vlm_reload_sync_reasoning(self):
        """Simulate an out-of-sync connection drop requiring reload."""
        frame = np.full((1080, 1920, 3), 40, dtype=np.uint8)
        cv2.rectangle(frame, (500, 300), (1420, 780), (70, 70, 70), -1)
        cv2.putText(frame, "Connection Lost", (680, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
        cv2.putText(frame, "Client out of sync", (680, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
        cv2.rectangle(frame, (800, 600), (1120, 680), (0, 180, 0), -1)
        cv2.putText(frame, "Reload", (880, 650), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        res = self.engine.analyze_screen(frame, force=True)
        self.assertFalse(res.is_dangerous)
        self.assertEqual(res.suggested_action, VLMActionType.DISMISS_POPUP)
        self.assertEqual(res.screen_classification, "RELOAD_SYNC")
        self.assertIsNotNone(res.target_coordinates)

    def test_vlm_caching_and_rate_limiting(self):
        """Verify identical frames return cached result within debounce window."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        res1 = self.engine.analyze_screen(frame, force=True)
        res2 = self.engine.analyze_screen(frame, force=False)
        self.assertEqual(res1.scene_summary, res2.scene_summary)
        self.assertEqual(res1.source_model, res2.source_model)

    def test_external_llm_decoupling_and_removal(self):
        """Verify the bot works 100% locally when external LLM is disabled or removed."""
        local_engine = MultimodalVLMEngine(enable_external=False)
        self.assertFalse(local_engine.has_external_llm())
        self.assertIsNone(local_engine.external_provider)

        # Frame analysis still works seamlessly via local heuristics
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        res = local_engine.analyze_screen(frame, force=True)
        self.assertIsNotNone(res)
        self.assertEqual(res.source_model, "local_florence_fallback")


if __name__ == "__main__":
    unittest.main()
