"""
Wall Planner.
Generates action plans for selecting wall segments, triggering batch multi-wall select,
and confirming wall upgrades with Gold or Elixir.
"""

from __future__ import annotations
from typing import List
from src.planning.deployment_planner import DeploymentAction, ActionType


class WallPlanner:
    """Plans wall selection and batch upgrading actions."""

    def __init__(self, batch_enabled: bool = True):
        self.batch_enabled = batch_enabled

    def generate_upgrade_plan(self, cycle_index: int = 0) -> List[DeploymentAction]:
        """Generates the click sequence to select a wall, trigger batch select, and confirm upgrade."""
        plan = []

        # 1. Tap a wall segment (sampling near center village grid)
        # Add slight variation per cycle so different wall groups are tested
        offset_x = ((cycle_index % 5) - 2) * 0.05
        offset_y = (((cycle_index // 5) % 5) - 2) * 0.05
        wall_x = 0.50 + offset_x
        wall_y = 0.50 + offset_y

        plan.append(DeploymentAction(
            action_type=ActionType.DEPLOY_POINT,
            target_name="wall_segment",
            norm_x=wall_x,
            norm_y=wall_y,
            delay_after_sec=0.4,
            description=f"Select wall segment at ({wall_x:.2f}, {wall_y:.2f})"
        ))

        # 2. If batch upgrade is enabled, click the "Select Row / Same Level" batch button
        if self.batch_enabled:
            plan.append(DeploymentAction(
                action_type=ActionType.CLICK_UI,
                target_name="batch_wall_select",
                norm_x=0.58,  # Typically next to the individual upgrade icon in bottom modal
                norm_y=0.85,
                delay_after_sec=0.3,
                description="Click batch wall select (all same level)"
            ))

        # 3. Click the Upgrade confirm button (Gold/Elixir button)
        plan.append(DeploymentAction(
            action_type=ActionType.CLICK_UI,
            target_name="upgrade_confirm",
            norm_x=0.50,
            norm_y=0.85,
            delay_after_sec=0.5,
            description="Confirm wall upgrade"
        ))

        return plan


# Backward compatibility alias
WallUpgradePlanner = WallPlanner
