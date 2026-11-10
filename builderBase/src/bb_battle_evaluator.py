"""
Builder Base Battle Evaluator.
Determines battle progress, hero ability triggers, and exit conditions.
"""

from __future__ import annotations
import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BBExitDecision(Enum):
    CONTINUE = "CONTINUE"
    SURRENDER = "SURRENDER"
    END_BATTLE = "END_BATTLE"
    RETURN_HOME = "RETURN_HOME"


class BBExitResult(BaseModel):
    decision: BBExitDecision
    reason: str = ""
    elapsed_seconds: float = 0.0


class BBBattleEvaluator:
    """Evaluates battle duration and exit conditions for Builder Base."""

    def __init__(self, exit_config=None):
        self.config = exit_config

    @property
    def combat_timer_seconds(self) -> float:
        if self.config and hasattr(self.config, "combat_timer_seconds"):
            try:
                val = float(self.config.combat_timer_seconds)
                return max(10.0, min(150.0, val))
            except (ValueError, TypeError):
                pass
        return 60.0

    def evaluate_exit(
        self,
        elapsed_combat_seconds: float,
        has_star_or_high_damage: bool = False
    ) -> BBExitResult:
        """Evaluates whether to exit battle based on user-configured timer."""
        limit = self.combat_timer_seconds

        if elapsed_combat_seconds >= limit:
            mins, secs = divmod(int(limit), 60)
            fmt = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
            decision = BBExitDecision.END_BATTLE if has_star_or_high_damage else BBExitDecision.SURRENDER
            return BBExitResult(
                decision=decision,
                reason=f"Combat timer reached limit of {fmt} ({elapsed_combat_seconds:.0f}s >= {limit:.0f}s)",
                elapsed_seconds=elapsed_combat_seconds
            )

        return BBExitResult(
            decision=BBExitDecision.CONTINUE,
            reason=f"Combat active ({elapsed_combat_seconds:.0f}s / {limit:.0f}s)",
            elapsed_seconds=elapsed_combat_seconds
        )
