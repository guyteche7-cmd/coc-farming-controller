"""
Session Controller.
Orchestrates worker threads, manages global Start/Pause/Stop/Bind hotkeys (F7/F8/F9/F10),
tracks high-level attack counters, provides audio/voice/toast feedback, and interfaces with the UI dashboard.
"""

from __future__ import annotations
import sys
import time
if sys.platform == "win32":
    import ctypes
else:
    ctypes = None
import threading
import logging
import uuid
from typing import Optional, Callable
from src.persistence.config_manager import ConfigManager, AppConfig
from src.persistence.database import DatabaseManager
from src.calibration.viewport import ViewportCalibrator
from src.capture.screen_capture import ScreenCapture
from src.capture.replay_adapter import ReplayScreenAdapter
from src.control.input_adapter import RealInputExecutor
from src.control.action_executor import ActionExecutor
from src.control.state_machine import StateMachine
from src.control.notifier import Notifier
from src.state.game_state import UIState, GameState
from src.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class SessionController:
    """Controls session execution, threading, and hardware hotkey listeners."""

    def __init__(
        self,
        config_manager: ConfigManager,
        db_manager: Optional[DatabaseManager] = None,
        state_callback: Optional[Callable[[UIState, GameState], None]] = None,
        notifier: Optional[Notifier] = None,
        window_bind_callback: Optional[Callable[[], None]] = None,
        hotkey_start_callback: Optional[Callable[[], None]] = None,
        hotkey_pause_callback: Optional[Callable[[], None]] = None,
        hotkey_stop_callback: Optional[Callable[[], None]] = None,
        verification_callback: Optional[Callable[[dict], None]] = None
    ):
        self.config_manager = config_manager
        self.config: AppConfig = config_manager.config
        self.db = db_manager or DatabaseManager(self.config.logging.database_file)
        self.state_callback = state_callback
        self.notifier = notifier or Notifier()
        self.window_bind_callback = window_bind_callback
        self.hotkey_start_callback = hotkey_start_callback
        self.hotkey_pause_callback = hotkey_pause_callback
        self.hotkey_stop_callback = hotkey_stop_callback
        self.verification_callback = verification_callback

        self.session_id = str(uuid.uuid4())[:8]
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_toggle_time = 0.0
        self.state_machine: Optional[StateMachine] = None
        self.last_loot_stats = {
            "total_gold": 0,
            "total_elixir": 0,
            "total_dark_elixir": 0,
            "last_gold": 0,
            "last_elixir": 0,
            "last_dark_elixir": 0,
        }

        # Lifetime cumulative statistics (persists across Start/Stop, only resets when program closes)
        self.lifetime_gold_looted: int = 0
        self.lifetime_elixir_looted: int = 0
        self.lifetime_dark_elixir_looted: int = 0
        self.lifetime_attacks_completed: int = 0
        self.lifetime_skips: int = 0
        self.attack_history_records: list = []

        # Viewport & Input
        self.calibrator = ViewportCalibrator(
            target_resolution=self.config.window.target_resolution,
            title_pattern=self.config.window.title_pattern
        )

        self._hotkey_listener_active = True
        self._setup_hotkeys()

    def _setup_hotkeys(self) -> None:
        """Starts hotkey listener thread (Win32 GetAsyncKeyState on Windows, pynput on macOS/Linux)."""
        if sys.platform == "win32" and ctypes and hasattr(ctypes, "windll"):
            threading.Thread(target=self._hardware_hotkey_poller, daemon=True).start()
            logger.info("Registered global hardware hotkeys: [F7] Bind Window, [F8] Start/Stop, [F9] Pause/Resume, [F10] Emergency Stop")
        else:
            threading.Thread(target=self._pynput_hotkey_listener, daemon=True).start()

    def _pynput_hotkey_listener(self) -> None:
        """Cross-platform global hotkey listener for macOS and Linux via pynput."""
        try:
            from pynput import keyboard
            modifiers = {"cmd": False, "ctrl": False}

            def on_press(key):
                if not self._hotkey_listener_active:
                    return False
                try:
                    # Track Command / Control modifiers
                    if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                        modifiers["cmd"] = True
                        return
                    if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                        modifiers["ctrl"] = True
                        return

                    # 1. Universal Escape Key -> Emergency Safe Stop
                    if key == keyboard.Key.esc:
                        logger.info("[HOTKEY] Esc pressed -> Emergency Safe Stop")
                        if self.hotkey_stop_callback:
                            self.hotkey_stop_callback()
                        else:
                            threading.Thread(target=self.stop_session, daemon=True).start()
                        return

                    # 2. Native macOS Command & Control Shortcuts (⌘R / Ctrl+R, ⌘P / Ctrl+P, ⌘B / Ctrl+B)
                    if modifiers["cmd"] or modifiers["ctrl"]:
                        char = getattr(key, "char", None)
                        if char:
                            c = char.lower()
                            if c == "r":
                                logger.info("[HOTKEY] ⌘R/Ctrl+R pressed -> Toggle Start/Stop")
                                if self.hotkey_start_callback:
                                    self.hotkey_start_callback()
                                else:
                                    threading.Thread(target=self.toggle_start_stop, daemon=True).start()
                                return
                            elif c == "p":
                                logger.info("[HOTKEY] ⌘P/Ctrl+P pressed -> Toggle Pause/Resume")
                                if self.hotkey_pause_callback:
                                    self.hotkey_pause_callback()
                                else:
                                    threading.Thread(target=self.toggle_pause, daemon=True).start()
                                return
                            elif c == "b":
                                logger.info("[HOTKEY] ⌘B/Ctrl+B pressed -> Bind Window")
                                if self.window_bind_callback:
                                    self.window_bind_callback()
                                else:
                                    threading.Thread(target=self.trigger_window_bind, daemon=True).start()
                                return

                    # 3. Standard Universal F-Keys (F7 Bind, F8 Start/Stop, F9 Pause, F10 Stop)
                    if key == keyboard.Key.f7:
                        logger.info("[HOTKEY] F7 pressed -> Bind Window")
                        if self.window_bind_callback:
                            self.window_bind_callback()
                        else:
                            threading.Thread(target=self.trigger_window_bind, daemon=True).start()
                    elif key == keyboard.Key.f8:
                        logger.info("[HOTKEY] F8 pressed -> Toggle Start/Stop")
                        if self.hotkey_start_callback:
                            self.hotkey_start_callback()
                        else:
                            threading.Thread(target=self.toggle_start_stop, daemon=True).start()
                    elif key == keyboard.Key.f9:
                        logger.info("[HOTKEY] F9 pressed -> Toggle Pause/Resume")
                        if self.hotkey_pause_callback:
                            self.hotkey_pause_callback()
                        else:
                            threading.Thread(target=self.toggle_pause, daemon=True).start()
                    elif key == keyboard.Key.f10:
                        logger.info("[HOTKEY] F10 pressed -> Emergency Stop")
                        if self.hotkey_stop_callback:
                            self.hotkey_stop_callback()
                        else:
                            threading.Thread(target=self.stop_session, daemon=True).start()
                except Exception:
                    pass

            def on_release(key):
                if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                    modifiers["cmd"] = False
                elif key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    modifiers["ctrl"] = False

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                logger.info("Registered cross-platform hotkeys via pynput: [⌘R/F8] Start/Stop, [⌘P/F9] Pause, [⌘B/F7] Bind, [Esc/F10] Safe Stop")
                while self._hotkey_listener_active:
                    time.sleep(0.5)
                listener.stop()
        except Exception as e:
            logger.debug(f"pynput hotkey listener not available: {e}. GUI controls remain fully active.")

    def _hardware_hotkey_poller(self) -> None:
        user32 = ctypes.windll.user32
        VK_F7 = 0x76
        VK_F8 = 0x77
        VK_F9 = 0x78
        VK_F10 = 0x79

        last_f7 = False
        last_f8 = False
        last_f9 = False
        last_f10 = False

        while self._hotkey_listener_active:
            try:
                f7 = bool(user32.GetAsyncKeyState(VK_F7) & 0x8000)
                f8 = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
                f9 = bool(user32.GetAsyncKeyState(VK_F9) & 0x8000)
                f10 = bool(user32.GetAsyncKeyState(VK_F10) & 0x8000)

                if f7 and not last_f7:
                    logger.info("[HOTKEY] F7 pressed -> Bind Window")
                    if self.window_bind_callback:
                        self.window_bind_callback()
                    else:
                        threading.Thread(target=self.trigger_window_bind, daemon=True).start()
                if f8 and not last_f8:
                    logger.info("[HOTKEY] F8 pressed -> Toggle Start/Stop")
                    if self.hotkey_start_callback:
                        self.hotkey_start_callback()
                    else:
                        threading.Thread(target=self.toggle_start_stop, daemon=True).start()
                if f9 and not last_f9:
                    logger.info("[HOTKEY] F9 pressed -> Toggle Pause/Resume")
                    if self.hotkey_pause_callback:
                        self.hotkey_pause_callback()
                    else:
                        threading.Thread(target=self.toggle_pause, daemon=True).start()
                if f10 and not last_f10:
                    logger.info("[HOTKEY] F10 pressed -> Emergency Stop")
                    if self.hotkey_stop_callback:
                        self.hotkey_stop_callback()
                    else:
                        threading.Thread(target=self.stop_session, daemon=True).start()

                last_f7 = f7
                last_f8 = f8
                last_f9 = f9
                last_f10 = f10
            except Exception:
                pass
            time.sleep(0.15)

    def trigger_window_bind(self) -> None:
        """Triggers interactive window binding."""
        if self.window_bind_callback:
            self.window_bind_callback()
        else:
            geom = self.calibrator.bind_foreground_window()
            self.notifier.announce(f"Bound to {geom.window_title or 'Game Window'}", chime="accept", toast_title="Window Bound")

    def toggle_start_stop(self) -> None:
        """Toggles session between running and stopped with 5.0s debounce (matches startup countdown)."""
        now = time.time()
        if now - self._last_toggle_time < 5.0:
            logger.debug(f"[HOTKEY] toggle_start_stop debounced (only {now - self._last_toggle_time:.2f}s since last toggle)")
            return
        self._last_toggle_time = now

        if self.is_running:
            self.stop_session()
        else:
            logger.info("Starting session via toggle...")
            self.start_session()


    def start_session(self, use_replay: bool = False, replay_adapter: Optional[ReplayScreenAdapter] = None) -> None:
        """Starts the autonomous controller loop on a worker thread."""
        if self.is_running:
            logger.warning("Session is already running.")
            return

        # Ensure any lingering previous thread has terminated cleanly
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            logger.info("Waiting for prior worker thread to stop...")
            self.is_running = False
            self._thread.join(timeout=1.5)

        self.session_id = str(uuid.uuid4())[:8]
        self.is_running = True
        self.is_paused = False
        self.db.start_session(self.session_id, self.config.mode)
        audit_logger.log_session_event("START_REQUESTED", self.session_id, f"Mode: {self.config.mode}")

        # Calibrate and focus game window immediately
        self.calibrator.calibrate_live_window()
        self.calibrator.focus_game_window()

        # Build shared vision components
        from src.vision.ocr_engine import OCREngine
        from src.vision.ai_detector import AIVisionDetector
        from src.vision.state_detector import UIStateDetector
        from src.vision.loot_detector import LootDetector
        from src.vision.battle_detector import BattleDetector
        from src.vision.wall_detector import WallDetector
        from src.rules.target_evaluator import TargetEvaluator
        from src.rules.battle_exit_evaluator import BattleExitEvaluator
        from src.rules.wall_evaluator import WallEvaluator
        from src.planning.deployment_planner import DeploymentPlanner
        from src.planning.wall_planner import WallPlanner

        ocr = OCREngine()
        ai = AIVisionDetector()

        state_detector   = UIStateDetector(ocr_engine=ocr, use_ai=True)
        loot_detector    = LootDetector(ocr_engine=ocr, ai_detector=ai)
        battle_detector  = BattleDetector(ocr_engine=ocr)
        wall_detector    = WallDetector(ocr_engine=ocr)

        target_evaluator    = TargetEvaluator(self.config.target)
        exit_evaluator      = BattleExitEvaluator(self.config.exit)
        wall_evaluator      = WallEvaluator(self.config.walls)
        ribbon_m = getattr(self.config.deployment, "ribbon_mode", "compact")
        lock_ribbon = getattr(self.config.deployment, "lock_ribbon_mode", True)
        deployment_planner  = DeploymentPlanner(
            edge=self.config.deployment.selected_edge,
            tap_delay=self.config.deployment.tap_delay_seconds,
            hero_delay=self.config.deployment.hero_tap_delay_seconds,
            spell_delay=self.config.deployment.spell_tap_delay_seconds,
            ribbon_mode=ribbon_m,
            lock_ribbon_mode=lock_ribbon,
        )
        wall_planner        = WallPlanner(batch_enabled=self.config.walls.prefer_batch_selection)

        # Input adapter — emulator only uses left clicks
        input_adapter = RealInputExecutor(self.calibrator, humanize=self.config.safety.humanize_mouse_movement)
        executor = ActionExecutor(input_adapter, calibrator=self.calibrator)
        mode_desc = "Win32 mouse interaction" if sys.platform == "win32" else "native mouse interaction"
        logger.info(f"Running in LIVE mode with {mode_desc}.")

        self.state_machine = StateMachine(
            config=self.config,
            state_detector=state_detector,
            loot_detector=loot_detector,
            battle_detector=battle_detector,
            wall_detector=wall_detector,
            target_evaluator=target_evaluator,
            deployment_planner=deployment_planner,
            exit_evaluator=exit_evaluator,
            wall_planner=wall_planner,
            action_executor=executor,
            notification_dispatcher=self.notifier,
            database=self.db,
            session_id=self.session_id,
            calibrator=self.calibrator,
            state_change_callback=self.state_callback,
            on_verification_prompt=self.verification_callback,
            config_manager=self.config_manager,
            on_attack_completed=self._on_attack_completed,
        )
        # Attach wall_evaluator separately (used in home state handler)
        self.state_machine.wall_evaluator = wall_evaluator

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info(f"Farming session {self.session_id} initialized (Mode: {self.config.mode})")


    def _worker_loop(self) -> None:
        worker_session_id = self.session_id

        # Guard: if stop was requested before thread even got scheduled, bail immediately
        if not self.is_running or self.session_id != worker_session_id:
            logger.info("Worker loop: session stopped before countdown began.")
            audit_logger.log_session_event("ABORTED_BEFORE_COUNTDOWN", worker_session_id)
            return

        # 5-second preparation & countdown window before starting clicks
        logger.info("Farming starts in 5 seconds... Focus Clash of Clans!")
        self.notifier.announce("Farming starts in 5 seconds", chime="ok", toast_title="Starting in 5s")
        audit_logger.log_session_event("COUNTDOWN_START", worker_session_id, "5-second preparation countdown initiated")

        for countdown in range(5, 0, -1):
            if not self.is_running or self.session_id != worker_session_id:
                logger.info("Farming startup cancelled during countdown.")
                audit_logger.log_session_event("COUNTDOWN_CANCELLED", worker_session_id, f"Stopped at {countdown}s")
                return
            logger.info(f"⏳ Starting in {countdown}s...")
            audit_logger.log_session_event("COUNTDOWN_TICK", worker_session_id, f"{countdown}s remaining")
            self.calibrator.focus_game_window()
            time.sleep(1.0)

        if not self.is_running or self.session_id != worker_session_id:
            return

        self.notifier.announce("Farming active! Starting attacks.", chime="accept", toast_title="Farming Active")
        logger.info(f"🚀 Farming session {self.session_id} is now ACTIVE.")
        audit_logger.log_session_event("SESSION_ACTIVE", worker_session_id, "Loop entered. Executing clicks.")

        while self.is_running and self.session_id == worker_session_id:
            try:
                if self.is_paused:
                    time.sleep(0.5)
                    continue

                # Check fixed attack mode limit
                if self.config.mode == "fixed_attacks" and self.state_machine.attacks_completed >= self.config.fixed_attack_count:
                    logger.info(f"Reached fixed attack limit ({self.config.fixed_attack_count}). Stopping session.")
                    self.notifier.announce(f"Completed target limit of {self.config.fixed_attack_count} attacks.", chime="victory", toast_title="Farming Completed")
                    audit_logger.log_session_event("FIXED_ATTACKS_REACHED", worker_session_id, f"{self.config.fixed_attack_count} attacks completed")
                    break

                self.state_machine.step()
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in state machine loop: {e}", exc_info=True)
                audit_logger.log_step_blocked(f"Exception in state machine loop: {e}")
                self.db.record_failure(self.session_id, str(self.state_machine.current_state), "LOOP_STEP", str(e))
                time.sleep(2.0)

        # Only reset session flags if this thread owns the active session!
        if self.session_id == worker_session_id:
            self.get_loot_stats()
            self.is_running = False
            self.is_paused = False
            self.db.end_session(self.session_id, "COMPLETED" if not getattr(self, "state_machine", None) or not self.state_machine.is_stopped else "STOPPED")
            logger.info(f"Session {self.session_id} finished.")
            audit_logger.log_session_event("SESSION_FINISHED", worker_session_id)
        else:
            logger.info(f"Worker thread for older session {worker_session_id} exited gracefully without affecting active session {self.session_id}.")

    def _on_attack_completed(self, attack_record: dict) -> None:
        """Callback invoked whenever an attack finishes on the result screen."""
        g = attack_record.get("target_gold", 0)
        e = attack_record.get("target_elixir", 0)
        de = attack_record.get("target_dark_elixir", 0)
        self.lifetime_gold_looted += g
        self.lifetime_elixir_looted += e
        self.lifetime_dark_elixir_looted += de
        self.lifetime_attacks_completed += 1
        self.last_loot_stats["last_gold"] = g
        self.last_loot_stats["last_elixir"] = e
        self.last_loot_stats["last_dark_elixir"] = de
        self.last_loot_stats["total_gold"] = self.lifetime_gold_looted
        self.last_loot_stats["total_elixir"] = self.lifetime_elixir_looted
        self.last_loot_stats["total_dark_elixir"] = self.lifetime_dark_elixir_looted
        self.attack_history_records.append(attack_record)
        logger.info(
            f"[LIFETIME LOOT] Attack #{self.lifetime_attacks_completed}: +{g:,} Gold, +{e:,} Elixir, +{de:,} DE. "
            f"Run Totals: {self.lifetime_gold_looted:,} Gold, {self.lifetime_elixir_looted:,} Elixir, {self.lifetime_dark_elixir_looted:,} DE"
        )

    def get_loot_stats(self) -> dict:
        """Returns the lifetime accumulated session loot (persisting across start/stop) and last attack loot."""
        sm_skips = getattr(self.state_machine, "consecutive_skips", 0) if self.state_machine else 0
        return {
            "total_gold": self.lifetime_gold_looted,
            "total_elixir": self.lifetime_elixir_looted,
            "total_dark_elixir": self.lifetime_dark_elixir_looted,
            "last_gold": self.last_loot_stats.get("last_gold", 0),
            "last_elixir": self.last_loot_stats.get("last_elixir", 0),
            "last_dark_elixir": self.last_loot_stats.get("last_dark_elixir", 0),
            "attacks_completed": self.lifetime_attacks_completed,
            "skips": self.lifetime_skips + sm_skips,
        }

    def toggle_pause(self) -> None:
        """Toggles pause/resume state with explicit voice, sound, and log feedback."""
        if not self.is_running:
            logger.warning("Cannot toggle pause: farming session is not active. Press F8 or click START FARMING first.")
            self.notifier.announce("Farming is not running. Press F8 to start.", chime="error", toast_title="Not Running")
            return

        self.is_paused = not self.is_paused
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.is_paused = self.is_paused

        status_str = "PAUSED" if self.is_paused else "RESUMED"
        logger.info(f"Farming session {status_str}")
        audit_logger.log_session_event(f"SESSION_{status_str}", getattr(self, "session_id", "N/A"))

        if self.is_paused:
            self.notifier.announce("Farming paused", chime="skip", toast_title="Farming Paused")
        else:
            self.notifier.announce("Farming resumed", chime="accept", toast_title="Farming Resumed")

    def confirm_deployment_verification(self, is_correct: bool, new_mode: Optional[str] = None) -> None:
        """Proxies deployment verification confirmation to active state machine."""
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.confirm_deployment_verification(is_correct, new_mode=new_mode)
            self.is_paused = self.state_machine.is_paused
        else:
            # Session not running, update config directly
            if hasattr(self.config, "deployment"):
                if is_correct:
                    self.config.deployment.deployment_verified = True
                    self.config.deployment.lock_ribbon_mode = True
                if new_mode:
                    self.config.deployment.ribbon_mode = new_mode
            self.config_manager.save_config(self.config)

    def request_deployment_verification(self) -> None:
        """Forces verification prompt on next attack."""
        if hasattr(self.config, "deployment"):
            self.config.deployment.verify_first_attack = True
            self.config.deployment.deployment_verified = False
            self.config_manager.save_config(self.config)
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.verify_first_attack = True
            self.state_machine.deployment_verified = False
        logger.info("[DEPLOYMENT VERIFICATION] Deployment verification will be requested after next attack.")

    def set_ribbon_mode(self, mode: str, locked: bool = True) -> None:
        """Updates ribbon mode in config and active planner."""
        if hasattr(self.config, "deployment"):
            self.config.deployment.ribbon_mode = mode
            self.config.deployment.lock_ribbon_mode = locked
            self.config_manager.save_config(self.config)
        if hasattr(self, "state_machine") and self.state_machine:
            self.state_machine.deployment_planner.set_ribbon_mode(mode, locked=locked)

    def stop_session(self) -> None:
        """Stops the farming session immediately with voice feedback."""
        if not self.is_running:
            return
        logger.info("Stopping farming session immediately...")
        self.get_loot_stats()
        audit_logger.log_session_event("STOP_REQUESTED", getattr(self, "session_id", "N/A"))
        self.is_running = False
        self.is_paused = False
        if hasattr(self, "state_machine") and self.state_machine:
            self.lifetime_skips += getattr(self.state_machine, "consecutive_skips", 0)
            self.state_machine.is_stopped = True
        self.notifier.announce("Farming session stopped", chime="error", toast_title="Farming Stopped")
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.5)
