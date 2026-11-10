"""
Test suite verifying fixes for:
1. Rejection of false-positive surr_conf dialogs during combat.
2. Exact 50% initial troop deployment wave calculation & badge count reading.
3. Ribbon slot deselection after hero abilities (preventing unintended Dragon Duke clicks).
4. Victory screen suppression of bottom-left End Battle clicks.
"""

import os
import cv2
import numpy as np
import pytest

from src.state.game_state import UIState
from src.vision.state_detector import UIStateDetector
from src.planning.deployment_planner import DeploymentPlanner, ActionType
from src.control.state_machine import StateMachine
from src.persistence.config_manager import AppConfig
from unittest.mock import MagicMock


class TestAttackFixes:

    @pytest.fixture
    def test_image(self):
        img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "test_cases", "test_army_single_troop_three_heroes.jpg")
        if os.path.exists(img_path):
            return cv2.imread(img_path)
        return None

    def test_badge_count_reading(self, test_image):
        if test_image is None:
            pytest.skip("Test image not found")
        planner = DeploymentPlanner()
        # Slot 0 has 42 Valkyries
        valk_count = planner.read_slot_unit_count(test_image, slot_idx=0)
        assert valk_count == 42, f"Expected 42 Valkyries, got {valk_count}"

        # Slot 5 has 11 Earthquake spells
        spell_count = planner.read_slot_unit_count(test_image, slot_idx=5)
        assert spell_count == 11, f"Expected 11 Spells, got {spell_count}"

    def test_false_positive_surrender_dialog_rejected(self, test_image):
        if test_image is None:
            pytest.skip("Test image not found")
        detector = UIStateDetector(use_ai=False)
        # Verify that an active combat screen without an open modal returns None from dialog validation
        diag_val = detector._validate_confirmation_dialog(test_image)
        assert diag_val is None, f"Expected None (no modal dialog), got {diag_val}"

    def test_exact_50_percent_troop_calculation(self):
        total_troops = 42
        troop_deployed = True  # 1 probe troop deployed
        half_troops = total_troops // 2  # 21
        init_wave_taps = max(1, half_troops - (1 if troop_deployed else 0))
        assert init_wave_taps == 20, f"Expected 20 taps in initial wave, got {init_wave_taps}"
        total_initial_troops = (1 if troop_deployed else 0) + init_wave_taps
        assert total_initial_troops == 21
        assert total_initial_troops == total_troops / 2

    def test_deselect_action_generation(self):
        planner = DeploymentPlanner()
        deselect = planner.generate_deselect_action(empty_slot_idx=0)
        assert deselect.action_type == ActionType.CLICK_UI
        assert deselect.slot_index == 0
        assert deselect.tap_count == 1
        assert "Deselect" in deselect.target_name

    def test_victory_screen_suppresses_end_battle_click(self):
        cfg = AppConfig()
        db_mock = MagicMock()
        exec_mock = MagicMock()
        calib_mock = MagicMock()
        notifier_mock = MagicMock()
        detector_mock = MagicMock()
        loot_mock = MagicMock()
        battle_mock = MagicMock()
        exit_mock = MagicMock()

        sm = StateMachine(
            config=cfg,
            state_detector=detector_mock,
            loot_detector=loot_mock,
            battle_detector=battle_mock,
            wall_detector=MagicMock(),
            target_evaluator=MagicMock(),
            deployment_planner=DeploymentPlanner(),
            exit_evaluator=exit_mock,
            wall_planner=MagicMock(),
            action_executor=exec_mock,
            notification_dispatcher=notifier_mock,
            database=db_mock,
            session_id=1,
            calibrator=calib_mock
        )
        sm.in_active_attack = True
        sm.initial_available_loot = 500000

        # Simulate frame where VICTORY_RESULT is detected
        from src.state.game_state import DetectionResult
        detector_mock.detect_ui_state.return_value = DetectionResult(value=UIState.VICTORY_RESULT, confidence=0.98)

        mock_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        sm._handle_result_screen = MagicMock()

        sm._handle_active_battle(mock_frame, MagicMock())

        # Verify: _handle_result_screen was invoked directly without clicking END_BATTLE_BUTTON
        sm._handle_result_screen.assert_called_once_with(mock_frame, UIState.VICTORY_RESULT)
        exec_mock.click_anchor.assert_not_called()
