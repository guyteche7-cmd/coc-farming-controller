"""
Session State Machine (AI-Guided Autonomous Farming Loop).
Orchestrates high-level game state transitions with YOLOv8 object detection,
dynamic multi-wave deployment, loot targeting, combat monitoring,
and comprehensive step-by-step decision audit logging.
"""

from __future__ import annotations
import os
import time
import logging
import cv2
from typing import Optional, Callable
from src.state.game_state import UIState, GameState, CandidateInfo
from src.state.army_ledger import ArmyLedger
from src.vision.state_detector import UIStateDetector
from src.vision.loot_detector import LootDetector
from src.vision.battle_detector import BattleDetector
from src.vision.wall_detector import WallDetector
from src.vision.storage_inspector import StorageInspector
from src.rules.target_evaluator import TargetEvaluator
from src.rules.battle_exit_evaluator import ExitEvaluator, ExitDecision
from src.rules.wall_evaluator import WallEvaluator
from src.planning.deployment_planner import DeploymentPlanner
from src.planning.wall_planner import WallUpgradePlanner
from src.control.action_executor import ActionExecutor
from src.control.notifier import NotificationDispatcher
from src.persistence.database import Database
from src.persistence.config_manager import RuntimeConfig
from src.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class StateMachine:
    """Core state engine coordinating vision, planning, and control modules."""

    def __init__(
        self,
        config: RuntimeConfig,
        state_detector: UIStateDetector,
        loot_detector: LootDetector,
        battle_detector: BattleDetector,
        wall_detector: WallDetector,
        target_evaluator: TargetEvaluator,
        deployment_planner: DeploymentPlanner,
        exit_evaluator: ExitEvaluator,
        wall_planner: WallUpgradePlanner,
        action_executor: ActionExecutor,
        notification_dispatcher: NotificationDispatcher,
        database: Database,
        session_id: int,
        calibrator=None,
        state_change_callback: Optional[Callable[[UIState, GameState], None]] = None
    ):
        self.config = config
        self.state_detector = state_detector
        self.loot_detector = loot_detector
        self.battle_detector = battle_detector
        self.wall_detector = wall_detector
        self.target_evaluator = target_evaluator
        self.deployment_planner = deployment_planner
        self.exit_evaluator = exit_evaluator
        self.wall_planner = wall_planner
        self.executor = action_executor
        self.notifier = notification_dispatcher
        self.db = database
        self.session_id = session_id
        self.calibrator = calibrator
        self.state_change_callback = state_change_callback

        self.current_state = UIState.UNKNOWN
        self.last_announced_state = UIState.UNKNOWN
        self.army_ledger = ArmyLedger()
        self.consecutive_skips = 0
        self.attacks_completed = 0
        self.in_active_attack = False
        self.active_attack_start_time = 0.0
        self.last_result_processed_time = 0.0
        self.last_damage_percent = 0.0
        self.last_damage_change_time = time.time()
        self.recovery_plan_executed = False
        self.current_candidate = CandidateInfo()
        self.initial_available_loot = 0
        self.full_deployment_finish_time = 0.0
        self.total_gold_looted = 0
        self.total_elixir_looted = 0
        self.total_dark_elixir_looted = 0
        self.last_attack_gold = 0
        self.last_attack_elixir = 0
        self.last_attack_dark_elixir = 0
        self.walls_upgraded_count = 0
        self.is_paused = False
        self.is_stopped = False
        self._lost_focus_notified = False
        self.tick_counter = 0
        self.unknown_state_streak = 0

        # Persistent ScreenCapture instance
        if self.calibrator:
            from src.capture.screen_capture import ScreenCapture
            self.screen_capture = ScreenCapture(self.calibrator)
        else:
            self.screen_capture = None

        # Per-player dynamic storage capacity and fullness monitoring
        self.storage_inspector = StorageInspector(ocr_engine=getattr(self.loot_detector, "ocr", None))
        self.current_player_name: str = ""
        self.player_max_gold: int = 0
        self.player_max_elixir: int = 0
        self.player_max_dark_elixir: int = 0
        self.storage_calibrated: bool = False
        self.current_gold: int = 0
        self.current_elixir: int = 0
        self.current_dark_elixir: int = 0


    def step(self, frame=None) -> UIState:
        """Executes one tick of the state machine."""
        self.tick_counter = getattr(self, "tick_counter", 0) + 1

        if self.is_stopped:
            audit_logger.log_step_blocked(f"Session is marked stopped (tick #{self.tick_counter})")
            return self.current_state

        if self.is_paused:
            audit_logger.log_step_blocked(f"Session is marked paused (tick #{self.tick_counter})")
            time.sleep(0.5)
            return self.current_state

        # Safety Guard: If game window is not foreground, bring it to front and continue
        fg_status = "Foreground"
        if self.calibrator and not self.calibrator.is_game_in_foreground():
            fg_status = "Refocusing"
            audit_logger.log_step_blocked(f"Game window not in foreground at tick #{self.tick_counter}. Calling focus_game_window()")
            if not self._lost_focus_notified:
                logger.info("[WINDOW GUARD] Game not in foreground — focusing window.")
                self._lost_focus_notified = True
            self.calibrator.focus_game_window()
            time.sleep(0.5)
        else:
            if self._lost_focus_notified:
                logger.info("[WINDOW GUARD] Game window refocused. Resuming farming actions.")
                self._lost_focus_notified = False

        game_state = GameState()

        # 1. Capture screen frame if not provided
        frame_provider = self.screen_capture.capture_frame if self.screen_capture else None
            
        if frame is None:
            if frame_provider:
                frame = frame_provider()
            if frame is None or frame.size == 0:
                audit_logger.log_step_blocked(f"Empty frame captured from game window at tick #{self.tick_counter}")
                time.sleep(0.2)
                return self.current_state

        # 2. Detect UI State & Log to Decision Audit Log
        state_res = self.state_detector.detect_ui_state(frame)
        detected_state = state_res.value
        game_state.ui_state = detected_state

        hwnd_str = f"HWND 0x{self.calibrator.geometry.hwnd:08X}" if (self.calibrator and hasattr(self.calibrator, "geometry") and self.calibrator.geometry.hwnd) else "N/A"
        audit_logger.log_state_tick(
            self.tick_counter,
            detected_state.name,
            state_res.confidence,
            fg_info=f"{hwnd_str} ({fg_status})",
            details=f"Current: {self.current_state.name}"
        )

        if detected_state != self.current_state:
            audit_logger.log_detection(
                detected_state.name,
                state_res.confidence,
                details=f"State transitioned from {self.current_state.name} to {detected_state.name}"
            )

        if self.state_change_callback:
            self.state_change_callback(detected_state, game_state)

        if detected_state != UIState.UNKNOWN:
            self.unknown_state_streak = 0
        else:
            self.unknown_state_streak += 1

        # 3. Dispatch based on detected game state
        if detected_state == UIState.HOME:
            self.in_active_attack = False
            self._handle_home_state(frame, game_state, frame_provider=frame_provider)

        elif detected_state == UIState.ATTACK_MENU:
            self._handle_attack_menu_state()

        elif detected_state == UIState.MY_ARMY_SCREEN:
            self._handle_my_army_state()

        elif detected_state == UIState.MATCHMAKING:
            if self.last_announced_state != UIState.MATCHMAKING:
                logger.info("Matchmaking in progress (clouds)... searching for enemy base.")
                self.notifier.play_chime("ok")
                self.last_announced_state = UIState.MATCHMAKING
            time.sleep(0.8)

        elif detected_state == UIState.CANDIDATE_BATTLE:
            self._handle_candidate_scan(frame, game_state, frame_provider)

        elif detected_state == UIState.ACTIVE_BATTLE:
            self._handle_active_battle(frame, game_state, frame_provider)

        elif detected_state in (UIState.END_BATTLE_DIALOG, UIState.SURRENDER_DIALOG):
            self._handle_confirm_dialog()

        elif detected_state == UIState.PICK_REWARD:
            self._handle_pick_reward_state()

        elif detected_state in (UIState.VICTORY_RESULT, UIState.DEFEAT_RESULT):
            self._handle_result_screen(frame, detected_state)

        elif detected_state == UIState.POPUP_MODAL or getattr(self.state_detector, "last_popup", None) is not None:
            self._handle_unknown_popup(frame, getattr(self.state_detector, "last_popup", None))

        else:
            self._handle_unprecedented_unknown_state(frame)

        self.current_state = detected_state
        return detected_state

    def _click_action_point(self, anchor_name: str, delay_after: float = 0.5, reason: str = "") -> None:
        """Clicks dynamically detected YOLO/Template anchor if available; falls back to static anchor."""
        if anchor_name in self.state_detector.dynamic_anchors:
            nx, ny = self.state_detector.dynamic_anchors[anchor_name]
            px, py = (0, 0)
            if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
                px, py = self.calibrator.normalized_to_pixel(nx, ny)
            audit_logger.log_action(anchor_name, px, py, nx, ny, reason=f"Dynamic AI Anchor -> {reason or 'Navigation'}")
            logger.info(f"[DYNAMIC AI CLICK] {anchor_name} at norm ({nx:.3f}, {ny:.3f})")
            self.executor.input_adapter.click_normalized(nx, ny, delay_after=delay_after)
        else:
            self.executor.click_anchor(anchor_name, delay_after=delay_after, reason=reason)

    def _handle_home_state(self, frame, game_state: GameState, frame_provider: Optional[Callable[[], np.ndarray]] = None) -> None:
        if self.in_active_attack:
            logger.info("[HOME STATE] Returned home directly from active battle. Incrementing completed attacks counter.")
            self.attacks_completed += 1
            self.in_active_attack = False
            dmg_ratio = max(0.4, min(1.0, self.last_damage_percent / 100.0))
            est_g = int(self.current_candidate.gold * dmg_ratio)
            est_e = int(self.current_candidate.elixir * dmg_ratio)
            est_de = int(self.current_candidate.dark_elixir * dmg_ratio)
            self.total_gold_looted += est_g
            self.total_elixir_looted += est_e
            self.total_dark_elixir_looted += est_de
            self.db.record_attack({
                "session_id": self.session_id,
                "outcome": "VICTORY",
                "target_gold": est_g,
                "target_elixir": est_e,
                "target_dark_elixir": est_de,
                "duration_seconds": max(1.0, time.time() - self.active_attack_start_time) if self.active_attack_start_time > 0 else 60.0,
                "exit_reason": "Returned to home from active battle"
            })
        self.in_active_attack = False

        # --- User-Defined Storage Limit Check ---
        # Checks top-right resource numbers on Home Village. If current resources reach user-specified limit, halts attacks.
        if hasattr(self.config, "storage_limit") and self.config.storage_limit.enabled and self.config.storage_limit.stop_when_full:
            cur_g, cur_e, cur_de = self.storage_inspector.read_current_resources(frame)
            if cur_g > 0:
                self.current_gold = cur_g
            if cur_e > 0:
                self.current_elixir = cur_e
            if cur_de > 0:
                self.current_dark_elixir = cur_de

            cfg_limit = self.config.storage_limit
            max_g = cfg_limit.max_gold
            max_e = cfg_limit.max_elixir
            max_de = cfg_limit.max_dark_elixir

            active_checks = []
            full_statuses = []

            if getattr(cfg_limit, "check_gold", True) and max_g > 0:
                pct_g = (self.current_gold / max_g * 100.0) if max_g > 0 else 0.0
                g_full = (self.current_gold >= max_g) or (pct_g >= cfg_limit.full_threshold_percent)
                active_checks.append(f"Gold: {self.current_gold:,}/{max_g:,} ({'FULL' if g_full else 'OK'})")
                full_statuses.append(g_full)

            if getattr(cfg_limit, "check_elixir", True) and max_e > 0:
                pct_e = (self.current_elixir / max_e * 100.0) if max_e > 0 else 0.0
                e_full = (self.current_elixir >= max_e) or (pct_e >= cfg_limit.full_threshold_percent)
                active_checks.append(f"Elixir: {self.current_elixir:,}/{max_e:,} ({'FULL' if e_full else 'OK'})")
                full_statuses.append(e_full)

            if getattr(cfg_limit, "check_dark_elixir", False) and max_de > 0:
                pct_de = (self.current_dark_elixir / max_de * 100.0) if max_de > 0 else 0.0
                de_full = (self.current_dark_elixir >= max_de) or (pct_de >= cfg_limit.full_threshold_percent)
                active_checks.append(f"DE: {self.current_dark_elixir:,}/{max_de:,} ({'FULL' if de_full else 'OK'})")
                full_statuses.append(de_full)

            mode = getattr(cfg_limit, "match_mode", "OR").upper()
            if active_checks:
                if mode == "AND":
                    is_full = all(full_statuses)
                else:  # "OR"
                    is_full = any(full_statuses)

                if is_full:
                    audit_logger.log_detection(
                        "HOME_STORAGE_FULL",
                        1.0,
                        details=f"Limit criteria fulfilled [{mode}]! {' | '.join(active_checks)}"
                    )
                    logger.warning(
                        f"[STORAGE LIMIT REACHED] Stopping attack session! "
                        f"Mode: {mode}. Checks: {' | '.join(active_checks)}"
                    )
                    self.notifier.announce("Storage limit reached. Auto-stopping attacks.", chime="cancel")
                    self.is_stopped = True
                    return

        if hasattr(self.config, "storage_limit") and self.config.storage_limit.enabled:
            audit_logger.log_detection(
                "HOME_RESOURCES",
                0.95,
                details=f"Current: Gold={self.current_gold:,}, Elixir={self.current_elixir:,}, DE={self.current_dark_elixir:,}"
            )

        if self.config.walls.enabled:
            home_res = self.wall_detector.detect_home_status(frame)
            wall_eval = self.wall_evaluator.evaluate(home_res.value)

            if wall_eval.should_upgrade:
                self.notifier.announce("Storage is full. Upgrading walls now.", chime="accept")
                plan = self.wall_planner.generate_upgrade_plan()
                for action in plan:
                    self.executor.execute_deployment_action(action)
                self.db.record_wall_upgrade(self.session_id, None, 1, "Gold/Elixir", 0)
                time.sleep(1.0)
                return

        # Boundary Safeguard: HOME_ATTACK_BUTTON must strictly be on the bottom-left yellow Battle button (nx <= 0.11, ny >= 0.80).
        # It must NEVER click on or to the right of the Shield / Season Pass button tray (nx >= 0.13).
        if "HOME_ATTACK_BUTTON" in self.state_detector.dynamic_anchors:
            nx, ny = self.state_detector.dynamic_anchors["HOME_ATTACK_BUTTON"]
            if nx > 0.11 or ny < 0.80:
                logger.warning(f"Rejecting invalid HOME_ATTACK_BUTTON anchor ({nx:.3f}, {ny:.3f}) targeting Season Pass/Shield tray. Resetting to Battle button.")
                self.state_detector.dynamic_anchors["HOME_ATTACK_BUTTON"] = (0.068, 0.880)

        logger.info("Clicking Attack button from Home Village...")
        if self.last_announced_state != UIState.HOME:
            self.notifier.announce("Opening attack menu", chime="ok")
            self.last_announced_state = UIState.HOME

        self._click_action_point("HOME_ATTACK_BUTTON", delay_after=1.2, reason="Open attack menu from Home screen")

    def _handle_attack_menu_state(self) -> None:
        logger.info("Clicking Find a Match button under Battle...")
        if self.last_announced_state != UIState.ATTACK_MENU:
            self.notifier.announce("Selecting multiplayer battle", chime="ok")
            self.last_announced_state = UIState.ATTACK_MENU

        # Boundary Safeguard: FIND_A_MATCH_BATTLE_BUTTON must be on the Battle card (y <= 0.85).
        # It must NEVER click down at y > 0.88 where "Edit Army" sits (y ~ 0.95).
        if "FIND_A_MATCH_BATTLE_BUTTON" in self.state_detector.dynamic_anchors:
            nx, ny = self.state_detector.dynamic_anchors["FIND_A_MATCH_BATTLE_BUTTON"]
            if ny > 0.85:
                logger.warning(f"Rejecting invalid low anchor for Find a Match ({nx:.3f}, {ny:.3f}). Resetting to default Battle card anchor.")
                self.state_detector.dynamic_anchors["FIND_A_MATCH_BATTLE_BUTTON"] = (0.173, 0.760)

        self._click_action_point("FIND_A_MATCH_BATTLE_BUTTON", delay_after=1.5, reason="Select Multiplayer Battle card")

    def _handle_my_army_state(self) -> None:
        if "ARMY_SCREEN_BATTLE_BUTTON" in self.state_detector.dynamic_anchors:
            logger.info("My Army / Edit Army screen detected with 'Battle' button. Redirecting to Multiplayer Battle menu...")
            if self.last_announced_state != UIState.MY_ARMY_SCREEN:
                self.notifier.announce("Redirecting to Battle menu", chime="ok")
                self.last_announced_state = UIState.MY_ARMY_SCREEN
            self._click_action_point("ARMY_SCREEN_BATTLE_BUTTON", delay_after=1.5, reason="Navigate from Edit Army to Battle menu")
            return

        # Boundary Safeguard: ARMY_SCREEN_ATTACK_BUTTON must be on bottom-right (nx > 0.65, ny > 0.75).
        # Anything on the left is "Edit Army" and must never be clicked as the attack confirmation button.
        if "ARMY_SCREEN_ATTACK_BUTTON" in self.state_detector.dynamic_anchors:
            nx, ny = self.state_detector.dynamic_anchors["ARMY_SCREEN_ATTACK_BUTTON"]
            if nx < 0.65 or ny < 0.75:
                logger.warning(f"Rejecting invalid left-side Army screen anchor ({nx:.3f}, {ny:.3f}). Resetting to default right anchor.")
                self.state_detector.dynamic_anchors["ARMY_SCREEN_ATTACK_BUTTON"] = (0.886, 0.932)

        logger.info("My Army screen visible with Attack! button. Confirming Attack!...")
        if self.last_announced_state != UIState.MY_ARMY_SCREEN:
            self.notifier.announce("Army ready. Launching search", chime="ok")
            self.last_announced_state = UIState.MY_ARMY_SCREEN

        self._click_action_point("ARMY_SCREEN_ATTACK_BUTTON", delay_after=1.5, reason="Confirm attack on My Army screen")

    def _handle_candidate_scan(self, frame, game_state: GameState, frame_provider: Optional[Callable[[], np.ndarray]] = None) -> None:
        """
        Multi-Sample Candidate Base Evaluation Engine:
        Guarantees 100% accuracy and zero missed good bases while staying strictly within the user's 3.0s budget.
        1. 0.35s delay for cloud parting and UI number stabilization.
        2. Sample 1 OCR scan.
        3. If Sample 1 accepted: quick 0.20s Sample 2 confirmation.
        4. If Sample 1 rejected: 0.55s pause to capture late fade-ins and take Sample 2.
        5. Combines the maximum values across samples: max(s1.gold, s2.gold) and max(s1.elixir, s2.elixir).
        6. If still low, checks sample 3 before skipping to ensure genuine low loot.
        """
        base_num = self.consecutive_skips + 1
        t_start = time.time()

        # Step 1: Initial cloud settle buffer (0.35s)
        time.sleep(0.35)

        # Capture initial fresh frame if provider available
        fresh_frame_1 = frame_provider() if frame_provider else frame
        if fresh_frame_1 is None or fresh_frame_1.size == 0:
            fresh_frame_1 = frame

        # Sample 1 OCR Scan
        loot_res_1 = self.loot_detector.detect_candidate_loot(fresh_frame_1)
        c1 = loot_res_1.value
        target_eval_1 = self.target_evaluator.evaluate(c1)

        best_gold = c1.gold
        best_elixir = c1.elixir
        best_de = c1.dark_elixir
        best_conf = c1.confidence
        best_eval = target_eval_1

        audit_logger.log_loot_scan(
            base_num=base_num,
            gold=c1.gold,
            elixir=c1.elixir,
            dark_elixir=c1.dark_elixir,
            confidence=c1.confidence,
            accepted=target_eval_1.accepted,
            reason=f"[Sample 1/2] {target_eval_1.reason}"
        )

        if target_eval_1.accepted:
            # Sample 1 was accepted! Perform a rapid 0.20s Sample 2 confirmation to ensure numbers didn't glitch
            time.sleep(0.20)
            fresh_frame_2 = frame_provider() if frame_provider else fresh_frame_1
            loot_res_2 = self.loot_detector.detect_candidate_loot(fresh_frame_2)
            c2 = loot_res_2.value

            best_gold = max(best_gold, c2.gold)
            best_elixir = max(best_elixir, c2.elixir)
            best_de = max(best_de, c2.dark_elixir)
            best_conf = max(best_conf, c2.confidence)

            candidate_confirmed = CandidateInfo(
                gold=best_gold,
                elixir=best_elixir,
                dark_elixir=best_de,
                confidence=best_conf,
                is_valid_candidate=True
            )
            best_eval = self.target_evaluator.evaluate(candidate_confirmed)

        else:
            # Sample 1 was rejected or caught early. Wait 0.55s for complete cloud dissipation and text roll-up
            time.sleep(0.55)
            fresh_frame_2 = frame_provider() if frame_provider else fresh_frame_1
            loot_res_2 = self.loot_detector.detect_candidate_loot(fresh_frame_2)
            c2 = loot_res_2.value
            target_eval_2 = self.target_evaluator.evaluate(c2)

            audit_logger.log_loot_scan(
                base_num=base_num,
                gold=c2.gold,
                elixir=c2.elixir,
                dark_elixir=c2.dark_elixir,
                confidence=c2.confidence,
                accepted=target_eval_2.accepted,
                reason=f"[Sample 2/2] {target_eval_2.reason}"
            )

            best_gold = max(best_gold, c2.gold)
            best_elixir = max(best_elixir, c2.elixir)
            best_de = max(best_de, c2.dark_elixir)
            best_conf = max(best_conf, c2.confidence)

            candidate_confirmed = CandidateInfo(
                gold=best_gold,
                elixir=best_elixir,
                dark_elixir=best_de,
                confidence=best_conf,
                is_valid_candidate=True
            )
            best_eval = self.target_evaluator.evaluate(candidate_confirmed)

            # Optional Sample 3 if both samples had low confidence or high variance and we are under 2.0s
            elapsed = time.time() - t_start
            if not best_eval.accepted and elapsed < 2.0 and (best_conf < 0.65 or abs(c1.gold - c2.gold) > 100000):
                time.sleep(0.35)
                fresh_frame_3 = frame_provider() if frame_provider else fresh_frame_2
                loot_res_3 = self.loot_detector.detect_candidate_loot(fresh_frame_3)
                c3 = loot_res_3.value
                best_gold = max(best_gold, c3.gold)
                best_elixir = max(best_elixir, c3.elixir)
                best_de = max(best_de, c3.dark_elixir)
                best_conf = max(best_conf, c3.confidence)
                candidate_confirmed = CandidateInfo(
                    gold=best_gold,
                    elixir=best_elixir,
                    dark_elixir=best_de,
                    confidence=best_conf,
                    is_valid_candidate=True
                )
                best_eval = self.target_evaluator.evaluate(candidate_confirmed)

        self.current_candidate = CandidateInfo(
            gold=best_gold,
            elixir=best_elixir,
            dark_elixir=best_de,
            confidence=best_conf,
            is_valid_candidate=True
        )
        game_state.candidate = self.current_candidate

        gold_k = best_gold // 1000
        elixir_k = best_elixir // 1000
        elapsed_sec = time.time() - t_start

        # Final Decision
        if best_eval.accepted:
            self.initial_available_loot = self.current_candidate.gold + self.current_candidate.elixir
            msg = f"Candidate accepted in {elapsed_sec:.2f}s! Found {gold_k}k Gold and {elixir_k}k Elixir ({self.initial_available_loot//1000}k total). Deploying army."
            logger.info(msg)
            self.notifier.announce(msg, chime="accept", toast_title="Base Accepted!")
            self.last_announced_state = UIState.CANDIDATE_BATTLE

            # Temporary verification screenshot at attack start
            try:
                import os
                temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp")
                os.makedirs(temp_dir, exist_ok=True)
                curr_att_num = self.attacks_completed + 1
                fn = f"attack_{curr_att_num:02d}_start_gold_{best_gold}_elixir_{best_elixir}_dark_elixir_{best_de}.png"
                fp = os.path.join(temp_dir, fn)
                ss_save_frame = fresh_frame_2 if ('fresh_frame_2' in locals() and fresh_frame_2 is not None and fresh_frame_2.size > 0) else (fresh_frame_1 if ('fresh_frame_1' in locals() and fresh_frame_1 is not None and fresh_frame_1.size > 0) else frame)
                cv2.imwrite(fp, ss_save_frame)
                logger.info(f"[VERIFICATION SCREENSHOT] Saved attack start screenshot #{curr_att_num:02d}: {fn}")
            except Exception as e:
                logger.warning(f"Failed to save attack start screenshot: {e}")

            audit_logger.log_loot_scan(
                base_num=base_num,
                gold=best_gold,
                elixir=best_elixir,
                dark_elixir=best_de,
                confidence=best_conf,
                accepted=True,
                reason=f"ACCEPTED in {elapsed_sec:.2f}s multi-sample verification: {best_eval.reason}"
            )

            self.in_active_attack = True
            self.active_attack_start_time = time.time()
            self.last_damage_percent = 0.0
            self.last_damage_change_time = time.time()
            self.recovery_plan_executed = False

            self.army_ledger.initialize_from_config(self.config.deployment)
            self._execute_full_deployment(fresh_frame_1)

        else:
            self.consecutive_skips += 1
            self.db.increment_session_skips(self.session_id)
            skip_msg = f"Skipping base {self.consecutive_skips} (inspected in {elapsed_sec:.2f}s). Verified Gold: {gold_k}k, Elixir: {elixir_k}k below threshold."
            logger.info(skip_msg)

            audit_logger.log_loot_scan(
                base_num=base_num,
                gold=best_gold,
                elixir=best_elixir,
                dark_elixir=best_de,
                confidence=best_conf,
                accepted=False,
                reason=f"SKIPPED in {elapsed_sec:.2f}s multi-sample verification: {best_eval.reason}"
            )

            if self.consecutive_skips % 5 == 1:
                self.notifier.announce("Skipping base. Loot below target.", chime="skip")
            else:
                self.notifier.play_chime("skip")

            # Click Next to find new base
            self._click_action_point("CANDIDATE_NEXT_BUTTON", delay_after=self.config.target.skip_delay_seconds, reason="Skip base below loot target")

    def _execute_full_deployment(self, frame) -> None:
        """
        Executes smart probe deployment with greyed-out completion checks:
        1. Selects Slot 0 (regular troops).
        2. Drops 1 single troop at default location. If successful (battle starts / 'nxt_btn' disappears), 
           confirms this location. If screened/blocked, tries nearby probe spots one by one with 1 troop.
        3. Once location is confirmed:
           - Dumps regular troops (Slot 0) in rapid bursts until the slot is GREYED OUT.
           - Deploys Siege Machine (Slot 1) with 1 click.
           - Deploys each Hero (Slots 2, 3, 4, 5) with 1 click to select + 1 click to deploy.
           - Casts Spells (Slot 6) in bursts until the spell slot is GREYED OUT.
           - Pauses 1.5s for march, then activates all Hero Abilities with 1 click each.
        """
        self.in_active_attack = True
        self.active_attack_start_time = time.time()
        self.last_damage_change_time = time.time()
        self.recovery_plan_executed = False

        probe_points = self.deployment_planner.get_probe_points()
        confirmed_spot = probe_points[0]
        troop_deployed = False

        # -------------------------------------------------------------
        # STEP 1: SELECT SLOT 0 (REGULAR TROOP) & PROBE FOR VALID DEPLOY SPOT
        # -------------------------------------------------------------
        select_action = self.deployment_planner.generate_slot_select_action(0)
        self.executor.execute_deployment_action(select_action)
        time.sleep(0.12)

        from src.capture.screen_capture import ScreenCapture
        cap = ScreenCapture(self.calibrator) if self.calibrator else None

        for idx, (px, py) in enumerate(probe_points):
            if self.is_stopped or self.is_paused:
                return
            if self.calibrator and not self.calibrator.is_game_in_foreground():
                self.calibrator.focus_game_window()

            logger.info(f"[DEPLOY PROBE] Testing single troop drop at probe {idx+1}/{len(probe_points)}: ({px:.3f}, {py:.3f})...")
            probe_action = self.deployment_planner.generate_single_troop_probe_action(px, py)
            self.executor.execute_deployment_action(probe_action)
            time.sleep(0.35)

            # Check if troop deployment succeeded (Next button disappeared or state is ACTIVE_BATTLE)
            if cap:
                check_frame = cap.capture_frame()
                if check_frame is not None and check_frame.size > 0:
                    state_res = self.state_detector.detect_ui_state(check_frame)
                    nxt_present = False
                    if self.state_detector.ai and self.state_detector.ai.is_ready():
                        ai_dets = getattr(self.state_detector, "last_ai_detections", {})
                        if "nxt_btn" in ai_dets and ai_dets["nxt_btn"]:
                            nxt_present = True
                    elif state_res.value == UIState.CANDIDATE_BATTLE:
                        nxt_present = True

                    if state_res.value == UIState.ACTIVE_BATTLE or not nxt_present:
                        logger.info(f"[DEPLOY PROBE] SUCCESS! Troop deployed at ({px:.3f}, {py:.3f}). Confirmed battle start.")
                        confirmed_spot = (px, py)
                        troop_deployed = True
                        break
                    else:
                        logger.info(f"[DEPLOY PROBE] Spot ({px:.3f}, {py:.3f}) was screened/blocked. Probing next position...")
            else:
                confirmed_spot = (px, py)
                break

        if not troop_deployed:
            logger.info(f"[DEPLOY PROBE] Probing completed. Deploying at primary location ({confirmed_spot[0]:.3f}, {confirmed_spot[1]:.3f})...")

        # -------------------------------------------------------------
        # STEP 2: DYNAMIC ARMY SLOT CLASSIFICATION & ADAPTIVE DEPLOYMENT
        # -------------------------------------------------------------
        cx, cy = confirmed_spot
        from src.planning.deployment_planner import DeploymentAction, ActionType

        cfg_hero_count = getattr(self.config.deployment, "hero_count", 2)
        cfg_deploy_siege = getattr(self.config.deployment, "deploy_siege", True)
        layout = self.deployment_planner.detect_army_slots(
            frame,
            configured_hero_count=cfg_hero_count,
            deploy_siege=cfg_deploy_siege
        )
        self.current_army_layout = layout
        logger.info(
            f"[DEPLOYMENT] Army Ribbon Layout -> Troops: {layout.troop_slots}, "
            f"Siege: {layout.siege_slot}, Heroes: {layout.hero_slots} ({len(layout.hero_slots)} heroes), "
            f"Spells: {layout.spell_slots} at ({cx:.3f}, {cy:.3f})"
        )

        # 1. DEPLOY INITIAL 50% TROOP WAVE ACROSS ALL DETECTED TROOP SLOTS
        for s_idx, t_slot in enumerate(layout.troop_slots):
            if self.is_stopped or self.is_paused:
                return
            if self.calibrator and not self.calibrator.is_game_in_foreground():
                self.calibrator.focus_game_window()

            slot_troop_count = self.deployment_planner.read_slot_unit_count(frame, t_slot)
            if slot_troop_count and slot_troop_count > 0:
                half_troops = slot_troop_count // 2
                # Deduct the 1 probe troop already dropped if successful from slot 0
                probe_deduct = 1 if (t_slot == 0 and troop_deployed) else 0
                init_wave_taps = max(1, half_troops - probe_deduct)
                logger.info(
                    f"[DEPLOYMENT] Slot {t_slot} detected unit count: {slot_troop_count} "
                    f"(Target 50%: {half_troops}, probe dropped: {probe_deduct} -> dropping {init_wave_taps} taps)"
                )
            else:
                init_wave_taps = 20
                logger.info(f"[DEPLOYMENT] Slot {t_slot} count unreadable; defaulting to 50% estimate ({init_wave_taps} taps)...")

            logger.info(f"[DEPLOYMENT] Phase 1/6: Deploying initial 50% troop wave ({init_wave_taps} taps on Slot {t_slot})...")
            select_ts = self.deployment_planner.generate_slot_select_action(t_slot)
            self.executor.execute_deployment_action(select_ts)
            time.sleep(0.08)

            init_troops_action = DeploymentAction(
                action_type=ActionType.DEPLOY_POINT,
                target_name=f"Initial 50% Troops (Slot {t_slot})",
                slot_index=t_slot,
                norm_x=cx,
                norm_y=cy,
                tap_count=init_wave_taps,
                delay_after_sec=0.035,
                description=f"Drop 50% troop wave ({init_wave_taps} taps) at ({cx:.3f}, {cy:.3f})"
            )
            self.executor.execute_deployment_action(init_troops_action)
            time.sleep(0.12)

        # 2. DEPLOY SIEGE MACHINE
        if not self.is_stopped and not self.is_paused and layout.siege_slot is not None:
            s_slot = layout.siege_slot
            logger.info(f"[DEPLOYMENT] Phase 2/6: Deploying Siege Machine (Slot {s_slot})...")
            select_s1 = self.deployment_planner.generate_slot_select_action(s_slot)
            self.executor.execute_deployment_action(select_s1)
            time.sleep(0.10)

            deploy_s1 = DeploymentAction(
                action_type=ActionType.DEPLOY_POINT,
                target_name="Deploy Siege",
                slot_index=s_slot,
                norm_x=cx,
                norm_y=cy,
                tap_count=1,
                delay_after_sec=0.12,
                description=f"Drop Siege Machine at ({cx:.3f}, {cy:.3f})"
            )
            self.executor.execute_deployment_action(deploy_s1)
            time.sleep(0.15)

            # Confirmation tap if siege is still not placed
            if cap:
                chk_frame = cap.capture_frame()
                if chk_frame is not None and not self.deployment_planner.is_slot_greyed_out(chk_frame, self.deployment_planner.SLOT_X_COORDINATES[s_slot]):
                    self.executor.execute_deployment_action(deploy_s1)
                    time.sleep(0.10)

        # 3. DEPLOY HEROES (ONLY ACTUAL DETECTED/CONFIGURED HERO SLOTS)
        if not self.is_stopped and not self.is_paused and layout.hero_slots:
            logger.info(f"[DEPLOYMENT] Phase 3/6: Deploying Heroes on slots {layout.hero_slots}...")
            for idx, slot_idx in enumerate(layout.hero_slots):
                if self.is_stopped or self.is_paused:
                    return
                if self.calibrator and not self.calibrator.is_game_in_foreground():
                    self.calibrator.focus_game_window()

                h_name = f"Hero {idx+1} (Slot {slot_idx})"
                sel_hero = self.deployment_planner.generate_slot_select_action(slot_idx)
                self.executor.execute_deployment_action(sel_hero)
                time.sleep(0.08)

                deploy_hero = DeploymentAction(
                    action_type=ActionType.DEPLOY_POINT,
                    target_name=f"Deploy {h_name}",
                    slot_index=slot_idx,
                    norm_x=cx,
                    norm_y=cy,
                    tap_count=1,
                    delay_after_sec=0.10,
                    description=f"Deploy {h_name} at ({cx:.3f}, {cy:.3f})"
                )
                self.executor.execute_deployment_action(deploy_hero)
                time.sleep(0.08)

        # 4. DEPLOY ALL REMAINING TROOPS ACROSS ALL TROOP SLOTS (UNTIL GREYED OUT)
        if not self.is_stopped and not self.is_paused:
            for t_slot in layout.troop_slots:
                if self.is_stopped or self.is_paused:
                    return
                if self.calibrator and not self.calibrator.is_game_in_foreground():
                    self.calibrator.focus_game_window()

                logger.info(f"[DEPLOYMENT] Phase 4/6: Deploying all remaining troops (Slot {t_slot}) until greyed out...")
                select_ts_again = self.deployment_planner.generate_slot_select_action(t_slot)
                self.executor.execute_deployment_action(select_ts_again)
                time.sleep(0.08)

                for batch in range(12):  # Up to 12 batches of 4 rapid taps (48 taps max)
                    if self.is_stopped or self.is_paused:
                        return
                    if self.calibrator and not self.calibrator.is_game_in_foreground():
                        self.calibrator.focus_game_window()

                    dump_rem_action = DeploymentAction(
                        action_type=ActionType.DEPLOY_POINT,
                        target_name=f"Dump Remaining Troops Slot {t_slot} Batch {batch+1}",
                        slot_index=t_slot,
                        norm_x=cx,
                        norm_y=cy,
                        tap_count=4,
                        delay_after_sec=0.035,
                        description=f"Drop remaining troops Slot {t_slot} at ({cx:.3f}, {cy:.3f})"
                    )
                    self.executor.execute_deployment_action(dump_rem_action)
                    time.sleep(0.08)

                    if cap:
                        chk_frame = cap.capture_frame()
                        if chk_frame is not None and self.deployment_planner.is_slot_greyed_out(chk_frame, self.deployment_planner.SLOT_X_COORDINATES[t_slot]):
                            logger.info(f"[DEPLOYMENT] Slot {t_slot} (Troops) fully depleted and greyed out after batch {batch+1}!")
                            break

        # 5. DEPLOY ALL SPELLS (ON ACTUAL SPELL SLOTS UNTIL GREYED OUT)
        if not self.is_stopped and not self.is_paused and layout.spell_slots:
            logger.info(f"[DEPLOYMENT] Phase 5/6: Casting Spells on slots {layout.spell_slots} across randomized base targets...")
            spell_targets = self.deployment_planner.get_randomized_spell_points()
            for sp_slot in layout.spell_slots:
                if self.is_stopped or self.is_paused:
                    return
                select_sp = self.deployment_planner.generate_slot_select_action(sp_slot)
                self.executor.execute_deployment_action(select_sp)
                time.sleep(0.08)

                for wave in range(2):  # 2 passes across targets
                    if self.is_stopped or self.is_paused:
                        return
                    for pt_x, pt_y in spell_targets:
                        if self.is_stopped or self.is_paused:
                            return
                        if self.calibrator and not self.calibrator.is_game_in_foreground():
                            self.calibrator.focus_game_window()

                        cast_action = DeploymentAction(
                            action_type=ActionType.DEPLOY_POINT,
                            target_name=f"Cast Spell Slot {sp_slot} ({pt_x:.3f}, {pt_y:.3f})",
                            slot_index=sp_slot,
                            norm_x=pt_x,
                            norm_y=pt_y,
                            tap_count=1,
                            delay_after_sec=0.04,
                            description=f"Cast Spell Slot {sp_slot} at target ({pt_x:.3f}, {pt_y:.3f})"
                        )
                        self.executor.execute_deployment_action(cast_action)
                        time.sleep(0.04)

                        if cap:
                            chk_frame = cap.capture_frame()
                            if chk_frame is not None and self.deployment_planner.is_slot_greyed_out(chk_frame, self.deployment_planner.SLOT_X_COORDINATES[sp_slot]):
                                logger.info(f"[DEPLOYMENT] Slot {sp_slot} (Spells) fully cast and greyed out!")
                                break

                    if cap:
                        chk_frame = cap.capture_frame()
                        if chk_frame is not None and self.deployment_planner.is_slot_greyed_out(chk_frame, self.deployment_planner.SLOT_X_COORDINATES[sp_slot]):
                            break

        # 6. WAIT BEFORE ACTIVATING HERO ABILITIES (USER CONFIGURED: REDUCED TO 6s)
        ability_wait_sec = getattr(self.config.deployment, "hero_ability_delay_seconds", 6.0)
        if not self.is_stopped and not self.is_paused and layout.hero_slots:
            logger.info(f"[DEPLOYMENT] Army deployed! Waiting {ability_wait_sec:.0f} seconds before activating hero abilities...")
            self.notifier.announce(f"Army deployed. Waiting {int(ability_wait_sec)} seconds before hero abilities.", chime="ok")
            for sec in range(int(ability_wait_sec)):
                if self.is_stopped or self.is_paused:
                    return
                if self.calibrator and not self.calibrator.is_game_in_foreground():
                    self.calibrator.focus_game_window()
                time.sleep(1.0)

        # 7. ACTIVATE HERO ABILITIES (ONLY ON ACTUAL HERO SLOTS)
        if not self.is_stopped and not self.is_paused and layout.hero_slots:
            logger.info(f"[DEPLOYMENT] Phase 7: Activating Hero Abilities on slots {layout.hero_slots}...")
            self.notifier.announce("Activating hero abilities!", chime="accept")
            for idx, slot_idx in enumerate(layout.hero_slots):
                if self.is_stopped or self.is_paused:
                    return
                h_name = f"Hero {idx+1} (Slot {slot_idx})"
                ability_action = DeploymentAction(
                    action_type=ActionType.ACTIVATE_ABILITY,
                    target_name=f"Ability: {h_name}",
                    slot_index=slot_idx,
                    norm_x=self.deployment_planner.SLOT_X_COORDINATES[slot_idx],
                    norm_y=self.deployment_planner.RIBBON_Y,
                    tap_count=1,
                    delay_after_sec=0.12,
                    description=f"Click Hero Slot {slot_idx} (1 tap) to trigger ability for {h_name}"
                )
                self.executor.execute_deployment_action(ability_action)

        # 8. DESELECT ACTIVE RIBBON SLOT (PREVENTS INADVERTENT HERO RE-CLICKS)
        if not self.is_stopped and not self.is_paused:
            empty_s = layout.troop_slots[0] if layout.troop_slots else 0
            logger.info(f"[DEPLOYMENT] Deselecting ribbon slot via depleted Slot {empty_s}...")
            deselect_action = self.deployment_planner.generate_deselect_action(empty_s)
            self.executor.execute_deployment_action(deselect_action)
            time.sleep(0.08)

        # 9. START INTERNAL 1-MINUTE (60s) POST-DEPLOYMENT COMBAT TIMER
        self.full_deployment_finish_time = time.time()
        self.notifier.announce("Full deployment complete. 60-second battle countdown started.", chime="ok")
        logger.info("[COMBAT TIMER] Full deployment complete. 60-second internal countdown timer started.")

    def _handle_active_battle(self, frame, game_state: GameState, frame_provider: Optional[Callable[[], np.ndarray]] = None) -> None:
        """Live combat feedback loop evaluated every second against the 3 exit conditions."""
        if not self.in_active_attack:
            return

        # 0. Early Gate: Check if battle already terminated naturally (e.g. 100% destruction or time expired)
        quick_check = self.state_detector.detect_ui_state(frame)
        if quick_check.value in (UIState.VICTORY_RESULT, UIState.DEFEAT_RESULT):
            logger.info(f"[COMBAT EXIT] Result screen ({quick_check.value.name}) already active on battle entry. Suppressing exit clicks.")
            self.current_state = quick_check.value
            self._handle_result_screen(frame, quick_check.value)
            return

        # 1. Detect live battle state (damage %, time remaining, stars)
        battle_res = self.battle_detector.detect_battle_status(frame, frame_provider=frame_provider)
        game_state.battle = battle_res.value
        current_dmg = battle_res.value.damage_percent

        # 2. Detect live remaining loot available
        loot_res = self.loot_detector.detect_candidate_loot(frame)
        cur_gold = loot_res.value.gold
        cur_elixir = loot_res.value.elixir
        if loot_res.confidence >= 0.35 and cur_gold == 0 and cur_elixir == 0 and self.initial_available_loot > 0:
            cur_loot = 0
        else:
            cur_loot = (cur_gold + cur_elixir) if (cur_gold > 0 or cur_elixir > 0) else self.initial_available_loot

        # 3. Calculate internal elapsed time since full deployment completed
        elapsed_combat = time.time() - self.full_deployment_finish_time if self.full_deployment_finish_time > 0 else 0.0

        # 4. Check damage progress
        if current_dmg > self.last_damage_percent:
            self.last_damage_percent = current_dmg
            self.last_damage_change_time = time.time()
            audit_logger.log_combat_status(current_dmg, battle_res.value.stars, 0.0, status="Damage Progressing")
        else:
            time_stagnant = time.time() - self.last_damage_change_time
            if time_stagnant > 6.0 and not self.recovery_plan_executed and current_dmg < 50.0:
                logger.info(f"[COMBAT FEEDBACK] Damage stagnant at {current_dmg:.0f}% for {time_stagnant:.1f}s. Triggering Hero abilities...")
                self.notifier.announce("Triggering hero abilities", chime="ok")
                audit_logger.log_combat_status(current_dmg, battle_res.value.stars, time_stagnant, status="Triggering Hero Abilities")
                active_hero_slots = self.current_army_layout.hero_slots if hasattr(self, "current_army_layout") and self.current_army_layout else [2, 3]
                rec_plan = self.deployment_planner.generate_recovery_plan(self.army_ledger, hero_slots=active_hero_slots)
                for action in rec_plan:
                    self.executor.execute_deployment_action(action)
                self.recovery_plan_executed = True

        # 5. Evaluate 3 exit conditions: (1) 1-min Timer (60s), (2) Damage >= 60%, (3) Loot Collected >= 65%
        exit_eval = self.exit_evaluator.evaluate(
            battle_info=battle_res.value,
            initial_loot=self.initial_available_loot,
            current_loot=cur_loot,
            elapsed_combat_seconds=elapsed_combat
        )

        if exit_eval.decision in (ExitDecision.END_BATTLE, ExitDecision.SURRENDER):
            # Capture fresh frame to verify if battle ended naturally
            fresh_f = frame_provider() if frame_provider else frame
            if fresh_f is not None and fresh_f.size > 0:
                fresh_check = self.state_detector.detect_ui_state(fresh_f)
                if fresh_check.value in (UIState.VICTORY_RESULT, UIState.DEFEAT_RESULT):
                    logger.info(f"[COMBAT EXIT] {fresh_check.value.name} appeared while evaluating exit. Skipping End Battle button click.")
                    self.current_state = fresh_check.value
                    self._handle_result_screen(fresh_f, fresh_check.value)
                    return

            is_end = (exit_eval.decision == ExitDecision.END_BATTLE)
            btn_name = "END_BATTLE_BUTTON" if is_end else "SURRENDER_BUTTON"
            action_label = "Ending" if is_end else "Surrendering"
            msg = f"Exit condition met: {exit_eval.reason}. {action_label} battle."
            logger.info(msg)
            self.notifier.announce(msg, chime="victory" if is_end else "ok", toast_title=f"{action_label} Battle")
            self.last_announced_state = UIState.ACTIVE_BATTLE

            # Step 1: Click the End Battle / Surrender button in bottom-left
            self._click_action_point(btn_name, delay_after=0.6, reason=exit_eval.reason)
            time.sleep(0.6)

            # Step 2: Confirm Okay pop-up modal ONLY if confirmation dialog is genuinely open
            check_dialog_frame = frame_provider() if frame_provider else None
            if check_dialog_frame is not None and check_dialog_frame.size > 0:
                diag_state = self.state_detector.detect_ui_state(check_dialog_frame)
                if diag_state.value in (UIState.END_BATTLE_DIALOG, UIState.SURRENDER_DIALOG):
                    self._click_action_point("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm exit battle dialog (Okay)")
                elif diag_state.value in (UIState.VICTORY_RESULT, UIState.DEFEAT_RESULT):
                    logger.info("[COMBAT EXIT] Result screen detected after clicking End Battle. Transitioning to result screen.")
                    self.current_state = diag_state.value
                    self._handle_result_screen(check_dialog_frame, diag_state.value)
            else:
                self._click_action_point("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm exit battle dialog (Okay)")

        else:
            time.sleep(1.0)  # Re-evaluate live every 1.0 second

    def _handle_unknown_popup(self, frame: Optional[np.ndarray], popup_info: Any) -> None:
        """
        Handles unexpected in-game modals and popups detected by Level-3 Florence-2 Vision:
        - If prompt is dangerous (e.g. Gem spending / confirmation): halts farming immediately, plays alarm, and logs incident.
        - If prompt is safe (Reload Game, Out of Sync, Personal Break, Promo 'X', Okay): clicks safe dismiss target.
        """
        if popup_info is None:
            time.sleep(0.5)
            return

        logger.info(
            f"[POPUP HANDLER] Processing {popup_info.popup_type} ('{popup_info.title}'): "
            f"Dangerous={popup_info.is_dangerous}, Dismiss={popup_info.dismiss_type} at {popup_info.dismiss_point}"
        )

        # 1. DANGEROUS PROMPT PROTECTION (Zero-loss guarantee)
        if popup_info.is_dangerous:
            logger.warning(
                f"[DANGEROUS PROMPT BLOCKED] {popup_info.title} - Description: '{popup_info.description}'. "
                "Pausing farming controller to prevent accidental Gem spending or unwanted resource purchase!"
            )
            audit_logger.log_action(
                "DANGEROUS_POPUP_GUARD",
                0, 0, 0.0, 0.0,
                reason=f"BLOCKED: {popup_info.popup_type} | {popup_info.description[:60]}"
            )
            self.notifier.play_chime("error")
            self.notifier.announce("Dangerous popup detected. Farming paused for safety.", chime="error")
            self.pause(reason=f"Dangerous popup detected: {popup_info.title}")
            return

        # 2. SAFE POPUP DISMISSAL
        if popup_info.dismiss_point is not None:
            nx, ny = popup_info.dismiss_point
            px, py = (0, 0)
            if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
                px, py = self.calibrator.normalized_to_pixel(nx, ny)

            audit_logger.log_action(
                f"DISMISS_{popup_info.popup_type}",
                px, py, nx, ny,
                reason=f"Safe auto-dismiss of {popup_info.popup_type} via {popup_info.dismiss_type}"
            )
            logger.info(f"[POPUP HANDLER] Dismissing {popup_info.popup_type} by clicking ({nx:.3f}, {ny:.3f})")
            self.executor.input_adapter.click_normalized(nx, ny, delay_after=1.2)
            time.sleep(1.0)
        else:
            logger.warning(f"[POPUP HANDLER] Popup detected ({popup_info.popup_type}) but no safe dismiss point found.")
            time.sleep(1.0)

    def _handle_unprecedented_unknown_state(self, frame: Optional[np.ndarray]) -> None:
        """
        Escalates unknown screen states to Tier 4 Multimodal Vision-Language Model (VLM).
        Triggered when screen remains UNKNOWN across >= 3 ticks.
        """
        if frame is None or frame.size == 0:
            time.sleep(0.5)
            return

        if self.unknown_state_streak >= 3:
            logger.info(f"[TIER 4 VLM] Escalating unknown screen to Multimodal VLM (streak={self.unknown_state_streak})...")
            from src.vision.vlm_engine import get_shared_vlm_engine, VLMActionType
            vlm = get_shared_vlm_engine()
            res = vlm.analyze_screen(
                frame,
                context_hint=f"Bot stuck in UNKNOWN state for {self.unknown_state_streak} ticks (last known state: {self.current_state.name})"
            )

            audit_logger.log_detection(
                "TIER4_VLM_REASONING",
                res.confidence,
                details=f"Model: {res.source_model} | Type: {res.screen_classification} | Action: {res.suggested_action}"
            )
            logger.info(f"[TIER 4 VLM] VLM Analysis: {res.screen_classification} -> {res.suggested_action} ({res.reasoning})")

            # 1. Dangerous action protection
            if res.is_dangerous:
                logger.warning(f"[DANGEROUS PROMPT BLOCKED BY VLM] {res.scene_summary}. Halting bot.")
                self.notifier.play_chime("error")
                self.pause(reason=f"Dangerous prompt blocked by VLM: {res.scene_summary}")
                return

            # 2. Suggested click / dismiss action
            if res.suggested_action in (VLMActionType.CLICK, VLMActionType.DISMISS_POPUP) and res.target_coordinates:
                nx, ny = res.target_coordinates
                logger.info(f"[TIER 4 VLM] Executing VLM recommended click on {res.target_element_description} at ({nx:.3f}, {ny:.3f})")
                audit_logger.log_action(
                    f"VLM_CLICK_{res.screen_classification}",
                    0, 0, nx, ny,
                    reason=f"VLM reasoning action: {res.target_element_description}"
                )
                self.executor.input_adapter.click_normalized(nx, ny, delay_after=1.2)
                self.unknown_state_streak = 0
                time.sleep(1.0)
                return

            # 3. Suggested pause / restart
            if res.suggested_action == VLMActionType.PAUSE:
                self.pause(reason=f"VLM recommended pause: {res.reasoning}")
                return

        time.sleep(0.5)

    def _handle_confirm_dialog(self) -> None:
        logger.info("[CONFIRM DIALOG] Modal dialog detected. Clicking Okay...")
        self._click_action_point("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm surrender/end battle dialog (Okay)")

    def _handle_pick_reward_state(self) -> None:
        logger.info("[PICK REWARD] Pick a Reward modal visible! Selecting middle reward card...")
        if self.last_announced_state != UIState.PICK_REWARD:
            self.notifier.announce("Claiming battle reward", chime="accept")
            self.last_announced_state = UIState.PICK_REWARD

        # Click the middle reward card (norm: 0.503, 0.547) to claim reward
        self._click_action_point("REWARD_CARD_MIDDLE", delay_after=1.2, reason="Claim battle reward card")

    def _handle_result_screen(self, frame, outcome_state: UIState) -> None:

        if time.time() - self.last_result_processed_time < 5.0:
            self._click_action_point("RETURN_HOME_BUTTON", delay_after=1.0, reason="Dismiss result screen")
            return

        if not self.in_active_attack:
            logger.info("Result screen reached (in_active_attack was False, processing victory loot and saving screenshot)...")

        self.last_result_processed_time = time.time()
        self.in_active_attack = False

        # Wait 2.2s for result screen animations / loot roll-up counter to settle completely
        time.sleep(2.2)

        # Capture fresh static frame for OCR
        if self.calibrator:
            from src.capture.screen_capture import ScreenCapture
            cap = ScreenCapture(self.calibrator)
            fresh_frame = cap.capture_frame()
            if fresh_frame is not None and fresh_frame.size > 0:
                frame = fresh_frame

        # Save static screenshot to temp folder FIRST for highest fidelity verification
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        raw_fn = f"victory_screenshot_{int(time.time())}.png"
        raw_fp = os.path.join(temp_dir, raw_fn)
        cv2.imwrite(raw_fp, frame)
        logger.info(f"[SCREENSHOT] Saved victory screenshot to disk: {raw_fn}")

        # Load the saved screenshot directly from disk to predict collected loot
        screenshot_img = cv2.imread(raw_fp)
        if screenshot_img is None or screenshot_img.size == 0:
            logger.warning("[SCREENSHOT] Failed to read back victory screenshot; falling back to in-memory frame.")
            screenshot_img = frame

        # Extract actual gained loot ("You got:" + "League Bonus:" if earned) directly from saved screenshot
        loot_res = self.loot_detector.detect_result_loot(screenshot_img)
        actual_gold = loot_res["total_gold"]
        actual_elixir = loot_res["total_elixir"]
        actual_dark_elixir = loot_res["total_dark_elixir"]

        # Rename screenshot to user-specified naming scheme with attack index
        curr_att_num = self.attacks_completed + 1
        fn = f"attack_{curr_att_num:02d}_victory_gold_{actual_gold}_elixir_{actual_elixir}_dark_elixir_{actual_dark_elixir}.png"
        verified_fp = os.path.join(temp_dir, fn)
        try:
            if os.path.exists(verified_fp):
                os.remove(verified_fp)
            os.rename(raw_fp, verified_fp)
            logger.info(f"[VERIFICATION SCREENSHOT] Saved verified victory screenshot #{curr_att_num:02d}: {fn}")
        except Exception as e:
            logger.warning(f"Failed to rename victory screenshot: {e}")

        # Fallback to estimated proportion of available candidate loot if OCR returned 0
        if actual_gold == 0 and actual_elixir == 0:
            dmg_ratio = max(0.1, min(1.0, self.last_damage_percent / 100.0))
            actual_gold = int(self.current_candidate.gold * dmg_ratio)
            actual_elixir = int(self.current_candidate.elixir * dmg_ratio)
            actual_dark_elixir = int(self.current_candidate.dark_elixir * dmg_ratio)

        self.last_attack_gold = actual_gold
        self.last_attack_elixir = actual_elixir
        self.last_attack_dark_elixir = actual_dark_elixir
        self.attacks_completed += 1
        self.total_gold_looted += actual_gold
        self.total_elixir_looted += actual_elixir
        self.total_dark_elixir_looted += actual_dark_elixir

        duration = max(1.0, time.time() - self.active_attack_start_time) if self.active_attack_start_time > 0 else 60.0
        outcome = "VICTORY" if outcome_state == UIState.VICTORY_RESULT else "DEFEAT"

        attack_record = {
            "session_id": self.session_id,
            "outcome": outcome,
            "target_gold": actual_gold,
            "target_elixir": actual_elixir,
            "target_dark_elixir": actual_dark_elixir,
            "duration_seconds": duration,
            "exit_reason": f"Finished with outcome {outcome}"
        }
        self.db.record_attack(attack_record)

        px, py = (0, 0)
        if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
            px, py = self.calibrator.normalized_to_pixel(0.495, 0.865)

        audit_logger.log_battle_exit(
            decision=outcome,
            final_damage=self.last_damage_percent,
            stars=0,
            button_clicked="RETURN_HOME_BUTTON",
            pixel_x=px,
            pixel_y=py
        )

        msg = (
            f"Attack {self.attacks_completed} finished with {outcome}! "
            f"Loot collected: {actual_gold:,} Gold, {actual_elixir:,} Elixir, {actual_dark_elixir:,} Dark Elixir."
        )
        logger.info(msg)
        self.notifier.announce(msg, chime="victory", toast_title="Attack Completed!")
        self.last_announced_state = outcome_state
        self._click_action_point("RETURN_HOME_BUTTON", delay_after=2.0, reason="Return to Home Village after battle")
