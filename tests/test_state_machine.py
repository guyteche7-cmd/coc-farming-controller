"""
End-to-End State Machine Integration Tests with Mock Adapters.
"""

import unittest
from unittest.mock import MagicMock
import numpy as np
from src.persistence.config_manager import AppConfig
from src.persistence.database import DatabaseManager
from src.control.input_adapter import DryRunExecutor
from src.control.action_executor import ActionExecutor
from src.control.state_machine import StateMachine
from src.rules.target_evaluator import TargetEvaluator
from src.rules.battle_exit_evaluator import ExitEvaluator
from src.rules.wall_evaluator import WallEvaluator
from src.planning.deployment_planner import DeploymentPlanner
from src.planning.wall_planner import WallUpgradePlanner
from src.calibration.viewport import ViewportCalibrator
from src.state.game_state import UIState, CandidateInfo, BattleInfo, HomeInfo, DetectionResult


class MockCaptureAdapter:
    def __init__(self):
        self.frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    def capture_frame(self):
        return self.frame


class TestStateMachine(unittest.TestCase):

    def setUp(self):
        self.config = AppConfig()
        self.calibrator = ViewportCalibrator()
        self.dry_adapter = DryRunExecutor(self.calibrator)
        self.executor = ActionExecutor(self.dry_adapter, calibrator=self.calibrator)
        self.db = DatabaseManager("data/test_history.db")
        self.mock_capture = MockCaptureAdapter()

        self.state_detector = MagicMock()
        self.state_detector.dynamic_anchors = {}
        self.state_detector.ai = None
        self.loot_detector = MagicMock()
        self.battle_detector = MagicMock()
        self.wall_detector = MagicMock()
        self.target_evaluator = TargetEvaluator(self.config.target)
        self.deployment_planner = DeploymentPlanner()
        self.exit_evaluator = ExitEvaluator(self.config.exit)
        self.wall_planner = WallUpgradePlanner()
        self.notifier = MagicMock()

        self.sm = StateMachine(
            config=self.config,
            state_detector=self.state_detector,
            loot_detector=self.loot_detector,
            battle_detector=self.battle_detector,
            wall_detector=self.wall_detector,
            target_evaluator=self.target_evaluator,
            deployment_planner=self.deployment_planner,
            exit_evaluator=self.exit_evaluator,
            wall_planner=self.wall_planner,
            action_executor=self.executor,
            notification_dispatcher=self.notifier,
            database=self.db,
            session_id=1,
            calibrator=self.calibrator
        )
        self.sm.wall_evaluator = WallEvaluator(self.config.walls)
        # Mock screen capture frame provider
        self.sm.screen_capture = self.mock_capture

    def test_candidate_acceptance_and_deployment(self):
        # Mock candidate state
        self.sm.state_detector.detect_ui_state = MagicMock(
            return_value=DetectionResult(value=UIState.CANDIDATE_BATTLE, confidence=0.95)
        )
        # Mock high loot candidate (1.2M Gold, 800k Elixir)
        self.sm.loot_detector.detect_candidate_loot = MagicMock(
            return_value=DetectionResult(
                value=CandidateInfo(gold=1200000, elixir=800000, confidence=0.90, is_valid_candidate=True),
                confidence=0.90
            )
        )

        initial_history_len = len(self.dry_adapter.action_history)
        next_state = self.sm.step(frame=self.mock_capture.frame)

        self.assertEqual(next_state, UIState.CANDIDATE_BATTLE)
        # Deployment actions should have been generated and dispatched
        self.assertGreater(len(self.dry_adapter.action_history), initial_history_len)

    def test_candidate_rejection_and_next_click(self):
        # Mock candidate state
        self.sm.state_detector.detect_ui_state = MagicMock(
            return_value=DetectionResult(value=UIState.CANDIDATE_BATTLE, confidence=0.95)
        )
        # Mock low loot candidate (300K Gold, 200K Elixir)
        self.sm.loot_detector.detect_candidate_loot = MagicMock(
            return_value=DetectionResult(
                value=CandidateInfo(gold=300000, elixir=200000, confidence=0.90, is_valid_candidate=True),
                confidence=0.90
            )
        )

        initial_skips = self.sm.consecutive_skips
        self.sm.step(frame=self.mock_capture.frame)

        self.assertEqual(self.sm.consecutive_skips, initial_skips + 1)
        # Last action should be NEXT button click
        last_action = self.dry_adapter.action_history[-1]
        self.assertEqual(last_action["action"], "CLICK")

    def test_battle_monitoring_50_percent_exit(self):
        self.sm.in_active_attack = True
        self.sm.state_detector.detect_ui_state = MagicMock(
            return_value=DetectionResult(value=UIState.ACTIVE_BATTLE, confidence=0.95)
        )
        # Mock 65% damage (exceeding default 60% damage threshold)
        self.sm.battle_detector.detect_battle_status = MagicMock(
            return_value=DetectionResult(
                value=BattleInfo(is_active=True, damage_percent=65.0, time_remaining_seconds=120),
                confidence=0.90
            )
        )
        self.sm.loot_detector.detect_candidate_loot = MagicMock(
            return_value=DetectionResult(
                value=CandidateInfo(gold=100000, elixir=100000, confidence=0.90, is_valid_candidate=True),
                confidence=0.90
            )
        )

        initial_len = len(self.dry_adapter.action_history)
        self.sm.step(frame=self.mock_capture.frame)

        # Should click END BATTLE button
        self.assertGreater(len(self.dry_adapter.action_history), initial_len)

    def test_home_wall_upgrade_trigger(self):
        self.config.mode = "wall_plus_attack"
        self.config.walls.enabled = True
        self.sm.state_detector.detect_ui_state = MagicMock(
            return_value=DetectionResult(value=UIState.HOME, confidence=0.95)
        )
        # Mock 90% Gold storage and 1 free builder
        self.sm.wall_detector.detect_home_status = MagicMock(
            return_value=DetectionResult(
                value=HomeInfo(gold_storage_fill_percent=90.0, elixir_storage_fill_percent=40.0, free_builders=1, total_builders=5),
                confidence=0.90
            )
        )

        initial_len = len(self.dry_adapter.action_history)
        self.sm.step(frame=self.mock_capture.frame)

        # Should have executed wall upgrade clicks
        self.assertGreater(len(self.dry_adapter.action_history), initial_len)


if __name__ == "__main__":
    unittest.main()
