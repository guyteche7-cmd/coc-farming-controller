"""
Battle Exit Decision Evaluator.
Evaluates 3 criteria on live battle state:
1. Combat Timer: 1 minute (60s) elapsed after full army deployment and hero abilities.
2. Overall Damage: >= 60% destruction.
3. Loot Collected: >= 65% of initial Gold + Elixir (remaining <= 35%).
Exits immediately if ANY of the three conditions is met.
"""

from __future__ import annotations
import logging
from enum import Enum
from pydantic import BaseModel
from src.state.game_state import BattleInfo

logger = logging.getLogger(__name__)


class ExitDecision(str, Enum):
    CONTINUE = "CONTINUE"
    END_BATTLE = "END_BATTLE"      # Exit via End Battle button
    SURRENDER = "SURRENDER"        # Exit via Surrender button


class ExitEvaluationResult(BaseModel):
    decision: ExitDecision
    reason: str
    damage_percent: float = 0.0
    time_remaining_seconds: int = 60
    loot_collected_percent: float = 0.0


class BattleExitEvaluator:
    """Evaluates whether the active battle should be terminated based on customizable post-deployment timer, damage, or loot thresholds."""

    DEFAULT_POST_DEPLOY_TIMER_SECONDS: float = 60.0 # 1 minute default
    MAX_COMBAT_TIMER_SECONDS: float = 150.0  # 2m 30s max limit
    DAMAGE_THRESHOLD_PERCENT: float = 60.0  # 60% destruction
    LOOT_COLLECTED_THRESHOLD_PCT: float = 65.0 # 65% of initial Gold + Elixir collected (remaining <= 35%)

    def __init__(self, exit_config=None):
        self.config = exit_config

    @property
    def post_deploy_timer_seconds(self) -> float:
        if self.config and hasattr(self.config, "combat_timer_seconds"):
            try:
                val = float(self.config.combat_timer_seconds)
                return max(5.0, min(self.MAX_COMBAT_TIMER_SECONDS, val))
            except (ValueError, TypeError):
                pass
        return self.DEFAULT_POST_DEPLOY_TIMER_SECONDS

    def evaluate(
        self,
        battle_info: BattleInfo,
        initial_loot: int = 0,
        current_loot: int = 0,
        elapsed_combat_seconds: float = 0.0
    ) -> ExitEvaluationResult:
        damage = battle_info.damage_percent
        timer_limit = self.post_deploy_timer_seconds

        damage_threshold = self.config.damage_threshold_percent if self.config and hasattr(self.config, "damage_threshold_percent") else self.DAMAGE_THRESHOLD_PERCENT
        loot_threshold = self.config.loot_collected_percent if self.config and hasattr(self.config, "loot_collected_percent") else self.LOOT_COLLECTED_THRESHOLD_PCT

        # Calculate loot collection percentage
        loot_collected_pct = 0.0
        if initial_loot > 0:
            collected = max(0, initial_loot - current_loot)
            loot_collected_pct = (collected / initial_loot) * 100.0

        # Choose exit button (End Battle when damage >= 50% / 1 star earned, otherwise Surrender)
        exit_type = ExitDecision.END_BATTLE if (damage >= 50.0 or battle_info.can_end_battle) else ExitDecision.SURRENDER

        # -------------------------------------------------------------
        # CONDITION 0: ALL AVAILABLE LOOT COLLECTED (0 Remaining Loot)
        # -------------------------------------------------------------
        if initial_loot > 0 and current_loot == 0:
            return ExitEvaluationResult(
                decision=ExitDecision.END_BATTLE,
                reason="All available loot collected (0 Gold and Elixir remaining). Ending battle immediately.",
                damage_percent=damage,
                time_remaining_seconds=int(max(0, timer_limit - elapsed_combat_seconds)),
                loot_collected_percent=100.0
            )

        # -------------------------------------------------------------
        # CONDITION 1: POST-DEPLOYMENT COMBAT TIMER (Max 2m 30s / 150s)
        # -------------------------------------------------------------
        if elapsed_combat_seconds >= timer_limit:
            mins, secs = divmod(int(timer_limit), 60)
            fmt_limit = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
            return ExitEvaluationResult(
                decision=exit_type,
                reason=f"Combat timer expired: {fmt_limit} ({elapsed_combat_seconds:.0f}s >= {timer_limit:.0f}s) elapsed after full deployment",
                damage_percent=damage,
                time_remaining_seconds=int(max(0, timer_limit - elapsed_combat_seconds)),
                loot_collected_percent=loot_collected_pct
            )

        # -------------------------------------------------------------
        # CONDITION 2: OVERALL DAMAGE >= THRESHOLD
        # -------------------------------------------------------------
        if damage >= damage_threshold:
            return ExitEvaluationResult(
                decision=ExitDecision.END_BATTLE,
                reason=f"Overall damage reached {damage:.0f}% (>= {damage_threshold:.0f}% target)",
                damage_percent=damage,
                time_remaining_seconds=int(max(0, timer_limit - elapsed_combat_seconds)),
                loot_collected_percent=loot_collected_pct
            )

        # -------------------------------------------------------------
        # CONDITION 3: LOOT COLLECTED >= THRESHOLD OF INITIAL
        # -------------------------------------------------------------
        if initial_loot > 0 and loot_collected_pct >= loot_threshold:
            rem_k = current_loot // 1000
            target_rem_k = int(initial_loot * (1.0 - (loot_threshold / 100.0))) // 1000
            tot_k = initial_loot // 1000
            return ExitEvaluationResult(
                decision=exit_type,
                reason=f"Loot collected reached {loot_collected_pct:.0f}% (Remaining {rem_k}k <= {target_rem_k}k of {tot_k}k target)",
                damage_percent=damage,
                time_remaining_seconds=int(max(0, timer_limit - elapsed_combat_seconds)),
                loot_collected_percent=loot_collected_pct
            )

        # No exit condition met: continue combat
        time_left_display = int(max(0, timer_limit - elapsed_combat_seconds)) if elapsed_combat_seconds > 0 else int(timer_limit)
        return ExitEvaluationResult(
            decision=ExitDecision.CONTINUE,
            reason=f"Combat active (timer: {time_left_display}s left, damage: {damage:.0f}% < 60%, loot collected: {loot_collected_pct:.0f}% < 65%)",
            damage_percent=damage,
            time_remaining_seconds=time_left_display,
            loot_collected_percent=loot_collected_pct
        )



# Backward compatibility alias
ExitEvaluator = BattleExitEvaluator


