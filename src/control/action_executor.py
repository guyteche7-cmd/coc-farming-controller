"""
Action Executor.
Executes high-level game navigation and deployment plans with pre-condition verification.
Integrates official Google Play Games keybindings (1, Z, Q, W, E, R, A) with physical clicks
and streams detailed feedback to the decision audit log.
"""

from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from src.control.input_adapter import BaseInputAdapter
from src.planning.deployment_planner import DeploymentAction, ActionType
from src.state.game_state import UIState, GameState
from src.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)


# Calibrated UI anchor positions in normalized coordinates (0.0 to 1.0)
UI_ANCHORS = {
    "HOME_ATTACK_BUTTON": (0.068, 0.880),              # Bottom-left "Battle" sword button on Home screen
    "FIND_A_MATCH_BUTTON": (0.173, 0.760),             # "Find a Match" under regular BATTLE card (left)
    "FIND_A_MATCH_BATTLE_BUTTON": (0.173, 0.760),      # Alias
    "ARMY_SCREEN_ATTACK_BUTTON": (0.886, 0.932),       # Green "Attack!" button on "My Army" screen
    "ARMY_SCREEN_BATTLE_BUTTON": (0.886, 0.898),       # Beige "Battle" button on "My Army" (opened via Edit Army)
    "CANDIDATE_NEXT_BUTTON": (0.913, 0.715),           # Orange "Next 1700" button in matchmaking
    "END_BATTLE_BUTTON": (0.071, 0.752),               # Red "End Battle" button in candidate battle
    "SURRENDER_BUTTON": (0.071, 0.752),                # Red "Surrender" button in active battle
    "CONFIRM_OKAY_BUTTON": (0.591, 0.622),             # Surrender / End Battle dialog green "Okay" button
    "CONFIRM_CANCEL_BUTTON": (0.409, 0.622),           # Surrender / End Battle dialog orange "Cancel" button
    "RETURN_HOME_BUTTON": (0.501, 0.865),              # Defeat/Victory screen green "Return Home" button
    "REWARD_CARD_LEFT": (0.295, 0.547),                # "Pick a Reward" Left Card
    "REWARD_CARD_MIDDLE": (0.503, 0.547),              # "Pick a Reward" Middle Card
    "REWARD_CARD_RIGHT": (0.712, 0.547),               # "Pick a Reward" Right Card
    "CLOUDS_RETURN_HOME_BUTTON": (0.055, 0.910),       # Villager Return Home on clouds screen
    "CLOSE_MODAL_X": (0.965, 0.098),                   # Top-right modal close X
    "HUD_GOLD_STORAGE": (0.880, 0.048),                # Top-right Gold storage HUD bar
    "HUD_ELIXIR_STORAGE": (0.880, 0.120),              # Top-right Elixir storage HUD bar
    "DISMISS_TOOLTIP_NEUTRAL": (0.500, 0.500)          # Village neutral center point to dismiss open tooltips
}

# Google Play Games Official Slot Keybinding Map
SLOT_KEYBINDINGS: Dict[int, str] = {
    0: "1",  # Slot 0: Troop 1 (Valkyries)
    1: "Z",  # Slot 1: Siege Machine (Log Launcher / Reinforcements)
    2: "Q",  # Slot 2: Hero 1 (Minion Prince / Pet)
    3: "W",  # Slot 3: Hero 2 (Archer Queen)
    4: "E",  # Slot 4: Hero 3 (Grand Warden)
    5: "R",  # Slot 5: Hero 4 (Barbarian King)
    6: "A",  # Slot 6: Spell 1 (Earthquake Spell)
}


class ActionResult(BaseModel):
    success: bool
    action_name: str
    message: str = ""
    duration_ms: float = 0.0


class ActionExecutor:
    """Dispatches validated actions to the input adapter."""

    def __init__(self, input_adapter: BaseInputAdapter, calibrator: Optional[Any] = None):
        self.input_adapter = input_adapter
        self.calibrator = calibrator

    def click_anchor(self, anchor_name: str, delay_after: float = 0.5, reason: str = "") -> ActionResult:
        """Clicks a named UI anchor point and audits action details."""
        if anchor_name not in UI_ANCHORS:
            return ActionResult(success=False, action_name=anchor_name, message=f"Unknown anchor {anchor_name}")

        nx, ny = UI_ANCHORS[anchor_name]
        px, py = (0, 0)
        if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
            px, py = self.calibrator.normalized_to_pixel(nx, ny)

        audit_logger.log_action(anchor_name, px, py, nx, ny, reason=reason)

        t0 = time.time()
        self.input_adapter.click_normalized(nx, ny, delay_after=delay_after)
        dt = (time.time() - t0) * 1000.0

        return ActionResult(success=True, action_name=anchor_name, duration_ms=dt)

    def execute_deployment_action(self, action: DeploymentAction) -> ActionResult:
        """
        Executes an individual DeploymentAction.
        Uses direct physical mouse clicks on the calibrated normalized coordinates
        to deploy units, select slots, and trigger abilities cleanly across all platforms
        (LDPlayer, BlueStacks, etc.) without relying on emulator hotkeys.
        """
        t0 = time.time()

        px, py = (0, 0)
        if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
            px, py = self.calibrator.normalized_to_pixel(action.norm_x, action.norm_y)

        if action.action_type == ActionType.SELECT_SLOT:
            audit_logger.log_deployment_step(
                action.slot_index, action.target_name, px, py, action.norm_x, action.norm_y,
                tap_count=1, desc="Selected unit slot on ribbon"
            )
            self.input_adapter.click_normalized(action.norm_x, action.norm_y, delay_after=action.delay_after_sec)

        elif action.action_type == ActionType.DEPLOY_POINT:
            audit_logger.log_deployment_step(
                action.slot_index, action.target_name, px, py, action.norm_x, action.norm_y,
                tap_count=action.tap_count, desc="Dropping units at target deployment spot"
            )
            for _ in range(max(1, action.tap_count)):
                self.input_adapter.click_normalized(action.norm_x, action.norm_y, delay_after=action.delay_after_sec)

        elif action.action_type == ActionType.ACTIVATE_ABILITY:
            audit_logger.log_hero_ability(
                action.slot_index or 0, action.target_name, px, py, action.norm_x, action.norm_y
            )
            self.input_adapter.click_normalized(action.norm_x, action.norm_y, delay_after=action.delay_after_sec)

        elif action.action_type == ActionType.CLICK_UI:
            self.input_adapter.click_normalized(action.norm_x, action.norm_y, delay_after=action.delay_after_sec)

        elif action.action_type == ActionType.WAIT:
            time.sleep(action.delay_after_sec)

        dt = (time.time() - t0) * 1000.0
        return ActionResult(success=True, action_name=action.target_name, duration_ms=dt)
