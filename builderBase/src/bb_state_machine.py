"""
Builder Base State Machine.
Orchestrates the autonomous Builder Base attack loop through all stages.
Logs detailed decision audit records via bb_audit.
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Callable, Any
from builderBase.src.bb_config_manager import BBConfig
from builderBase.src.bb_state_detector import BBStateDetector, BBUIState, BBDetectionResult
from builderBase.src.bb_deployment_planner import BBDeploymentPlanner, BBActionType
from builderBase.src.bb_battle_evaluator import BBBattleEvaluator, BBExitDecision
from builderBase.src.bb_audit_logger import bb_audit

logger = logging.getLogger(__name__)


class BBStateMachine:
    """Manages state transitions and actions for Builder Base attacks."""

    def __init__(
        self,
        config: BBConfig,
        state_detector: Optional[BBStateDetector] = None,
        deployment_planner: Optional[BBDeploymentPlanner] = None,
        battle_evaluator: Optional[BBBattleEvaluator] = None,
        input_adapter: Optional[Any] = None,
        calibrator: Optional[Any] = None,
        notifier: Optional[Any] = None,
        state_change_callback: Optional[Callable[[BBUIState, dict], None]] = None
    ):
        self.config = config
        self.state_detector = state_detector or BBStateDetector()
        self.deployment_planner = deployment_planner or BBDeploymentPlanner(
            default_point=tuple(config.deployment.default_point),
            tap_delay=config.deployment.tap_delay_seconds,
            slot_delay=config.deployment.slot_delay_seconds
        )
        self.battle_evaluator = battle_evaluator or BBBattleEvaluator(config.exit)
        self.input_adapter = input_adapter
        self.calibrator = calibrator
        self.notifier = notifier
        self.state_change_callback = state_change_callback

        self.current_state: BBUIState = BBUIState.UNKNOWN
        self.attacks_completed: int = 0
        self.in_active_battle: bool = False
        self.stage1_deployed: bool = False
        self.stage2_deployed: bool = False
        self.combat_start_time: float = 0.0
        self.last_result_time: float = 0.0

    def _click_anchor(self, anchor_name: str, delay_after: float = 0.5, reason: str = "") -> None:
        """Clicks normalized anchor coordinates via input adapter and logs audit record."""
        if anchor_name in self.state_detector.dynamic_anchors:
            nx, ny = self.state_detector.dynamic_anchors[anchor_name]
        elif anchor_name in self.state_detector.DEFAULT_ANCHORS:
            nx, ny = self.state_detector.DEFAULT_ANCHORS[anchor_name]
        else:
            logger.warning(f"Unknown anchor: {anchor_name}")
            return

        px, py = None, None
        if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
            try:
                px, py = self.calibrator.normalized_to_pixel(nx, ny)
            except Exception:
                pass

        bb_audit.log_click(anchor_name, nx, ny, px, py, reason=reason)
        logger.info(f"[BB ACTION] Click {anchor_name} at norm ({nx:.3f}, {ny:.3f}) | {reason}")

        if self.input_adapter and hasattr(self.input_adapter, "click_normalized"):
            self.input_adapter.click_normalized(nx, ny, delay_after=delay_after)
        else:
            time.sleep(delay_after)

    def step(self, frame) -> BBUIState:
        """Processes a single video frame, detects state, and executes corresponding action."""
        res: BBDetectionResult = self.state_detector.detect_ui_state(frame)
        detected_state = res.state

        if detected_state != self.current_state:
            logger.info(f"[BB STATE] Transition: {self.current_state.name} -> {detected_state.name} ({res.details})")
            self.current_state = detected_state
            if self.state_change_callback:
                self.state_change_callback(detected_state, {"attacks": self.attacks_completed})

        # -------------------------------------------------------------
        # STATE DISPATCH
        # -------------------------------------------------------------
        if detected_state == BBUIState.BB_HOME:
            self._handle_home_state()

        elif detected_state == BBUIState.BB_START_ATTACK_MODAL:
            self._handle_start_attack_modal()

        elif detected_state == BBUIState.BB_MATCHMAKING:
            time.sleep(0.8)

        elif detected_state == BBUIState.BB_BATTLE_COUNTDOWN:
            # "Battle starts in: Xs" — do nothing, wait for countdown to finish
            logger.info("[BB COUNTDOWN] Pre-battle countdown active. Waiting for timer to hit 0s...")
            time.sleep(1.0)

        elif detected_state == BBUIState.BB_STAGE1_BATTLE:
            self._handle_stage1_battle(res.active_troop_slots)

        elif detected_state == BBUIState.BB_STAGE2_BATTLE:
            self._handle_stage2_battle(res.active_troop_slots)

        elif detected_state == BBUIState.BB_CONFIRM_DIALOG:
            self._handle_confirm_dialog()

        elif detected_state == BBUIState.BB_RESULT_SCREEN:
            self._handle_result_screen()

        else:
            time.sleep(0.5)

        return detected_state

    def _handle_home_state(self) -> None:
        self.in_active_battle = False
        self.stage1_deployed = False
        self.stage2_deployed = False

        if self.config.mode == "fixed_attacks" and self.attacks_completed >= self.config.fixed_attack_count:
            logger.info(f"[BB] Reached target attack count ({self.attacks_completed}/{self.config.fixed_attack_count}). Finished.")
            bb_audit.log_session_event("COMPLETED", "Fixed attack goal reached", f"{self.attacks_completed}/{self.config.fixed_attack_count} attacks")
            if self.notifier and hasattr(self.notifier, "announce"):
                self.notifier.announce(f"Builder Base session complete! {self.attacks_completed} attacks performed.", chime="victory")
            time.sleep(2.0)
            return

        logger.info("[BB] Opening Attack Menu from Home...")
        self._click_anchor("ATTACK_BUTTON", delay_after=1.0, reason="Click Attack! button on Home Village")

    def _handle_start_attack_modal(self) -> None:
        logger.info("[BB] Clicking 'Find Now!' on Start Attack modal...")
        self._click_anchor("FIND_NOW_BUTTON", delay_after=1.2, reason="Find Now! match search")

    def _handle_stage1_battle(self, active_slots: list[int]) -> None:
        self.in_active_battle = True

        if not self.stage1_deployed:
            logger.info(f"[BB] Stage 1 detected ({len(active_slots)} troop slots detected). Executing deployment sequence...")
            logger.info("[BB] Waiting 6 seconds before deploying troops (allowing map to settle)...")
            time.sleep(6.0)
            bb_audit.log_detection("BB_STAGE1_BATTLE", 1.0, "Initiating Stage 1 army deployment", active_slots)
            if self.notifier and hasattr(self.notifier, "announce"):
                self.notifier.announce("Deploying Builder Base army", chime="ok")

            plan = self.deployment_planner.generate_stage1_plan(active_slots)
            for tap_idx, action in enumerate(plan, 1):
                if action.target_norm_pos:
                    px, py = None, None
                    if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
                        try:
                            px, py = self.calibrator.normalized_to_pixel(action.target_norm_pos[0], action.target_norm_pos[1])
                        except Exception:
                            pass
                    bb_audit.log_deployment(action.description, action.slot_index or 0, tap_idx, len(plan), action.target_norm_pos[0], action.target_norm_pos[1], px, py)

                if action.target_norm_pos and self.input_adapter and hasattr(self.input_adapter, "click_normalized"):
                    self.input_adapter.click_normalized(action.target_norm_pos[0], action.target_norm_pos[1], delay_after=action.delay_after)
                else:
                    time.sleep(action.delay_after)

            self.stage1_deployed = True
            self.combat_start_time = time.time()
            logger.info("[BB] Stage 1 army fully deployed! Combat timer started.")
            return

        # Battle ongoing: only evaluate exit conditions, no ability activation
        now = time.time()
        elapsed = now - self.combat_start_time

        exit_res = self.battle_evaluator.evaluate_exit(elapsed)
        bb_audit.log_combat_status(elapsed, exit_res.decision.name, exit_res.reason)

        if exit_res.decision in (BBExitDecision.SURRENDER, BBExitDecision.END_BATTLE):
            btn = "END_BATTLE_BUTTON" if exit_res.decision == BBExitDecision.END_BATTLE else "SURRENDER_BUTTON"
            logger.info(f"[BB EXIT] {exit_res.reason} -> Clicking {btn}")
            self._click_anchor(btn, delay_after=0.4, reason=exit_res.reason)
            time.sleep(0.4)
            self._click_anchor("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm exit dialog (Okay)")

    def _handle_stage2_battle(self, active_slots: list[int]) -> None:
        self.in_active_battle = True

        if not self.stage2_deployed:
            logger.info(f"[BB] Stage 2 detected! Deploying Stage 2 Reinforcements...")
            bb_audit.log_detection("BB_STAGE2_BATTLE", 1.0, "Initiating Stage 2 reinforcement deployment", active_slots)
            if self.notifier and hasattr(self.notifier, "announce"):
                self.notifier.announce("Deploying Stage 2 reinforcements", chime="ok")

            plan = self.deployment_planner.generate_stage2_reinforcement_plan(active_slots)
            for tap_idx, action in enumerate(plan, 1):
                if action.target_norm_pos:
                    px, py = None, None
                    if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
                        try:
                            px, py = self.calibrator.normalized_to_pixel(action.target_norm_pos[0], action.target_norm_pos[1])
                        except Exception:
                            pass
                    bb_audit.log_deployment(action.description, action.slot_index or 0, tap_idx, len(plan), action.target_norm_pos[0], action.target_norm_pos[1], px, py)

                if action.target_norm_pos and self.input_adapter and hasattr(self.input_adapter, "click_normalized"):
                    self.input_adapter.click_normalized(action.target_norm_pos[0], action.target_norm_pos[1], delay_after=action.delay_after)
                else:
                    time.sleep(action.delay_after)

            self.stage2_deployed = True
            logger.info("[BB] Stage 2 Reinforcements deployed!")
            return

        # Battle ongoing: only evaluate exit conditions, no ability activation
        now = time.time()
        elapsed = now - self.combat_start_time

        exit_res = self.battle_evaluator.evaluate_exit(elapsed)
        bb_audit.log_combat_status(elapsed, exit_res.decision.name, exit_res.reason)

        if exit_res.decision in (BBExitDecision.SURRENDER, BBExitDecision.END_BATTLE):
            btn = "END_BATTLE_BUTTON" if exit_res.decision == BBExitDecision.END_BATTLE else "SURRENDER_BUTTON"
            logger.info(f"[BB EXIT] {exit_res.reason} -> Clicking {btn}")
            self._click_anchor(btn, delay_after=0.4, reason=exit_res.reason)
            time.sleep(0.4)
            self._click_anchor("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm exit dialog (Okay)")

    def _handle_confirm_dialog(self) -> None:
        logger.info("[BB] Modal dialog visible. Clicking Okay...")
        self._click_anchor("CONFIRM_OKAY_BUTTON", delay_after=0.8, reason="Confirm dialog Okay")

    def _handle_result_screen(self) -> None:
        # Guard: If no attack was actually conducted, simply dismiss without incrementing attack counter
        if not self.in_active_battle:
            logger.info("[BB RESULT] Result screen detected without active combat in progress. Dismissing...")
            self._click_anchor("RETURN_HOME_BUTTON", delay_after=1.0, reason="Dismiss result screen")
            return

        if time.time() - self.last_result_time < 3.0:
            self._click_anchor("RETURN_HOME_BUTTON", delay_after=1.0, reason="Dismiss result screen")
            return

        self.last_result_time = time.time()
        self.attacks_completed += 1
        self.in_active_battle = False
        self.stage1_deployed = False
        self.stage2_deployed = False

        bb_audit.log_attack_summary(self.attacks_completed, self.config.fixed_attack_count, status="VICTORY / COMPLETED")
        logger.info(f"[BB RESULT] Attack finished! Total attacks completed: {self.attacks_completed}")
        if self.notifier and hasattr(self.notifier, "announce"):
            self.notifier.announce(f"Builder Base attack {self.attacks_completed} finished!", chime="victory")

        time.sleep(1.0)
        self._click_anchor("RETURN_HOME_BUTTON", delay_after=1.2, reason="Return Home from Result Screen")
