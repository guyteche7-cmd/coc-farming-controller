"""
Builder Base Session Controller.
Manages the lifecycle, input executors, viewport calibration, and execution thread for Builder Base.
Logs all lifecycle and error events to bb_audit.
"""

from __future__ import annotations
import time
import uuid
import ctypes
import traceback
import logging
import threading
from typing import Optional, Callable, Any
from builderBase.src.bb_config_manager import BBConfigManager, BBConfig
from builderBase.src.bb_state_detector import BBStateDetector, BBUIState
from builderBase.src.bb_deployment_planner import BBDeploymentPlanner
from builderBase.src.bb_battle_evaluator import BBBattleEvaluator
from builderBase.src.bb_state_machine import BBStateMachine
from builderBase.src.bb_audit_logger import bb_audit

# Import core infrastructure adapters from src
try:
    from src.calibration.viewport import ViewportCalibrator
    from src.capture.screen_capture import ScreenCapture
    from src.control.input_adapter import RealInputExecutor
    from src.control.notifier import Notifier
except ImportError:
    ViewportCalibrator = None
    ScreenCapture = None
    RealInputExecutor = None
    Notifier = None

logger = logging.getLogger(__name__)


class BBSessionController:
    """Controls the background worker loop for Builder Base farming."""

    def __init__(
        self,
        config_manager: Optional[BBConfigManager] = None,
        state_callback: Optional[Callable[[BBUIState, dict], None]] = None,
        notifier: Optional[Any] = None,
        calibrator: Optional[Any] = None
    ):
        self.config_manager = config_manager or BBConfigManager()
        self.config: BBConfig = self.config_manager.config
        self.state_callback = state_callback
        self.notifier = notifier or (Notifier() if Notifier else None)

        self.session_id = str(uuid.uuid4())[:8]
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None

        self.calibrator = calibrator or (ViewportCalibrator() if ViewportCalibrator else None)
        self.input_adapter = RealInputExecutor(self.calibrator, humanize=self.config.safety.humanize_mouse_movement) if RealInputExecutor and self.calibrator else None
        self.capture = ScreenCapture(self.calibrator) if ScreenCapture and self.calibrator else None

        self.state_machine = BBStateMachine(
            config=self.config,
            input_adapter=self.input_adapter,
            calibrator=self.calibrator,
            notifier=self.notifier,
            state_change_callback=self.state_callback
        )

    def start_session(self) -> None:
        """Starts the Builder Base attack loop in a worker thread."""
        if self.is_running:
            logger.warning("Builder Base session is already running.")
            return

        self.session_id = str(uuid.uuid4())[:8]
        self.is_running = True
        self.is_paused = False

        if self.calibrator:
            self.calibrator.calibrate_live_window()
            self.calibrator.focus_game_window()

        self.input_adapter = RealInputExecutor(self.calibrator, humanize=self.config.safety.humanize_mouse_movement) if RealInputExecutor and self.calibrator else None
        self.capture = ScreenCapture(self.calibrator) if ScreenCapture and self.calibrator else None

        self.state_machine = BBStateMachine(
            config=self.config,
            input_adapter=self.input_adapter,
            calibrator=self.calibrator,
            notifier=self.notifier,
            state_change_callback=self.state_callback
        )

        bb_audit.log_session_event("STARTED", self.session_id, f"Mode: {self.config.mode} | Target Attacks: {self.config.fixed_attack_count}")

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info(f"Builder Base session {self.session_id} started on thread.")
        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce("Builder Base bot started", chime="ok")

    def stop_session(self) -> None:
        """Stops the Builder Base attack loop."""
        if not self.is_running:
            return
        self.is_running = False
        self.is_paused = False
        bb_audit.log_session_event("STOPPED", self.session_id, f"Completed attacks: {self.state_machine.attacks_completed}")
        logger.info(f"Builder Base session {self.session_id} stopped.")
        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce("Builder Base bot stopped", chime="warning")

    def toggle_pause(self) -> None:
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        status = "Paused" if self.is_paused else "Resumed"
        bb_audit.log_session_event(status.upper(), self.session_id)
        logger.info(f"Builder Base session {status}.")
        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce(f"Builder Base bot {status.lower()}", chime="ok")

    def _worker_loop(self) -> None:
        """Main execution loop running in background."""
        if not self.is_running:
            logger.info("BB worker loop: session stopped before countdown began.")
            return

        # 5-second preparation & countdown window before starting clicks
        logger.info("Builder Base attack starts in 5 seconds... Focus Clash of Clans!")
        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce("Builder Base starts in 5 seconds", chime="ok", toast_title="Starting in 5s")

        for countdown in range(5, 0, -1):
            if not self.is_running:
                logger.info("Builder Base startup cancelled during countdown.")
                return
            logger.info(f"⏳ Starting in {countdown}s...")
            time.sleep(1.0)

        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce("Builder Base active! Starting attacks.", chime="ok", toast_title="Session Active")
        logger.info(f"🚀 Builder Base session {self.session_id} is now ACTIVE.")

        while self.is_running:
            if self.is_paused:
                time.sleep(0.5)
                continue

            try:
                # Window focus check (guard)
                if self.calibrator and hasattr(self.calibrator, "is_game_in_foreground"):
                    if not self.calibrator.is_game_in_foreground():
                        title = getattr(self.calibrator.geometry, "window_title", "")
                        bb_audit.log_focus_guard(False, title)
                        logger.info("[BB FOCUS GUARD] Clash of Clans lost foreground. Waiting for focus...")
                        time.sleep(1.0)
                        continue

                if self.capture:
                    frame = self.capture.capture_frame()
                    if frame is not None and frame.size > 0:
                        self.state_machine.step(frame)
                    else:
                        time.sleep(0.4)
                else:
                    time.sleep(0.5)

            except Exception as e:
                exc_str = traceback.format_exc()
                bb_audit.log_error("BBSessionController.worker", str(e), exc_str)
                logger.error(f"[BB WORKER ERROR] {e}", exc_info=True)
                time.sleep(1.0)
