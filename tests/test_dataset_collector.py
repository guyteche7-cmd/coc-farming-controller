import os
import time
import shutil
import numpy as np
import pytest
from unittest.mock import MagicMock

from src.control.state_machine import StateMachine
from src.state.game_state import UIState
from src.persistence.config_manager import AppConfig, DatasetConfig


def test_dataset_collector_saves_frame(tmp_path):
    test_dir = str(tmp_path / "dataset_test")
    cfg = AppConfig()
    cfg.dataset = DatasetConfig(
        enabled=True,
        interval_seconds=2.0,
        save_dir=test_dir,
        capture_combat=True,
        capture_home=True
    )

    sm = StateMachine(
        config=cfg,
        state_detector=MagicMock(),
        loot_detector=MagicMock(),
        battle_detector=MagicMock(),
        wall_detector=MagicMock(),
        target_evaluator=MagicMock(),
        deployment_planner=MagicMock(),
        exit_evaluator=MagicMock(),
        wall_planner=MagicMock(),
        action_executor=MagicMock(),
        notification_dispatcher=MagicMock(),
        database=MagicMock(),
        session_id=1,
        calibrator=None
    )

    frame = np.full((100, 100, 3), 128, dtype=np.uint8)

    # First trigger should collect
    sm._maybe_collect_dataset_frame(frame, UIState.ACTIVE_BATTLE)
    time.sleep(0.3)  # Allow async thread to write

    files = os.listdir(test_dir)
    assert len(files) == 1
    assert "ACTIVE_BATTLE" in files[0]
    assert files[0].endswith(".jpg")

    # Immediate second trigger should be throttled by interval
    sm._maybe_collect_dataset_frame(frame, UIState.ACTIVE_BATTLE)
    time.sleep(0.1)
    files2 = os.listdir(test_dir)
    assert len(files2) == 1  # Still 1 because interval hasn't passed

    # Clean up
    shutil.rmtree(test_dir, ignore_errors=True)
