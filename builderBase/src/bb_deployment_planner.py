"""
Builder Base Deployment Planner.
Generates structured, safe cascade deployment plans for Hero, Troops, and Stage 2 Reinforcements.
Uses natural human-cadence taps to auto-cycle army camps without ever touching the bottom bar twice.
"""

from __future__ import annotations
import random
import logging
from enum import Enum
from typing import List, Tuple, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BBActionType(Enum):
    SELECT_SLOT = "SELECT_SLOT"
    TAP_SCREEN = "TAP_SCREEN"
    WAIT = "WAIT"


class BBDeploymentAction(BaseModel):
    action_type: BBActionType
    slot_index: Optional[int] = None
    target_norm_pos: Optional[Tuple[float, float]] = None
    delay_after: float = 0.20
    description: str = ""


class BBDeploymentPlanner:
    """Plans safe cascade deployment sequences for Builder Base attacks."""

    # Calibrated deployment spot (black dot from reference image: top-right perimeter)
    DEFAULT_DEPLOYMENT_SPOT: Tuple[float, float] = (0.776, 0.102)

    # Slot positions in bottom bar
    SLOT_POSITIONS: dict[int, Tuple[float, float]] = {
        0: (0.098, 0.833), # Hero Slot (Battle Machine / Battle Copter)
        1: (0.188, 0.833),
        2: (0.265, 0.833),
        3: (0.342, 0.833),
        4: (0.419, 0.833),
        5: (0.496, 0.833),
        6: (0.573, 0.833),
        7: (0.650, 0.833), # Reinforcement 1
        8: (0.727, 0.833), # Reinforcement 2
    }

    def __init__(
        self,
        default_point: Optional[Tuple[float, float]] = None,
        tap_delay: float = 0.20,
        slot_delay: float = 0.30
    ):
        self.default_point = default_point or self.DEFAULT_DEPLOYMENT_SPOT
        self.tap_delay = max(0.18, tap_delay)
        self.slot_delay = max(0.25, slot_delay)

    def get_deployment_point(self, randomize: bool = True) -> Tuple[float, float]:
        """Returns the deployment target point with slight natural jitter."""
        nx, ny = self.default_point
        if randomize:
            jitter_x = random.uniform(-0.012, 0.012)
            jitter_y = random.uniform(-0.012, 0.012)
            return (max(0.05, min(0.95, nx + jitter_x)), max(0.05, min(0.95, ny + jitter_y)))
        return (nx, ny)

    def generate_stage1_plan(self, active_slots: List[int]) -> List[BBDeploymentAction]:
        """
        Generates safe cascade deployment for Stage 1:
        1. Select Hero Slot 0 -> Tap battlefield 1x (places Hero).
        2. Select Troop Slot 1 -> Tap battlefield continuously (24 taps at ~0.20s).
           CoC automatically cycles from Slot 1 -> 2 -> 3 -> 4 -> 5 -> 6.
        3. Zero clicks on the bottom bar afterwards -> Never triggers any abilities!
        """
        actions: List[BBDeploymentAction] = []
        deploy_pt = self.get_deployment_point(randomize=False)

        # Step 1: Deploy Hero (Slot 0)
        actions.append(BBDeploymentAction(
            action_type=BBActionType.SELECT_SLOT,
            slot_index=0,
            target_norm_pos=self.SLOT_POSITIONS[0],
            delay_after=self.slot_delay,
            description="Select Hero (Slot 0)"
        ))
        actions.append(BBDeploymentAction(
            action_type=BBActionType.TAP_SCREEN,
            target_norm_pos=self.get_deployment_point(randomize=True),
            delay_after=0.35,
            description=f"Deploy Hero at {deploy_pt}"
        ))

        # Step 2: Select First Troop Camp (Slot 1)
        actions.append(BBDeploymentAction(
            action_type=BBActionType.SELECT_SLOT,
            slot_index=1,
            target_norm_pos=self.SLOT_POSITIONS[1],
            delay_after=self.slot_delay,
            description="Select First Troop Camp (Slot 1)"
        ))

        # Step 3: Cascade Continuous Drops (24 natural taps at ~0.20s)
        # Sufficient for all camps (P.E.K.K.As, Giants, Archers, Barbarians, etc.)
        num_taps = 24
        for tap_i in range(1, num_taps + 1):
            pt = self.get_deployment_point(randomize=True)
            actions.append(BBDeploymentAction(
                action_type=BBActionType.TAP_SCREEN,
                target_norm_pos=pt,
                delay_after=self.tap_delay,
                description=f"Cascade Deploy Army (Tap {tap_i}/{num_taps})"
            ))

        return actions

    def generate_stage2_reinforcement_plan(self, active_slots: List[int]) -> List[BBDeploymentAction]:
        """
        Generates safe cascade deployment for Stage 2 Reinforcements (Slots 7 & 8):
        1. Select Slot 7 (first reinforcement camp)
        2. Tap battlefield continuously (12 taps at ~0.20s) to deploy both reinforcement camps.
        3. Zero clicks on bottom bar afterwards.
        """
        actions: List[BBDeploymentAction] = []

        # Step 1: Select First Reinforcement Camp (Slot 7)
        actions.append(BBDeploymentAction(
            action_type=BBActionType.SELECT_SLOT,
            slot_index=7,
            target_norm_pos=self.SLOT_POSITIONS[7],
            delay_after=self.slot_delay,
            description="Select Reinforcements (Slot 7)"
        ))

        # Step 2: Cascade Continuous Drops (12 taps at ~0.20s)
        num_taps = 12
        for tap_i in range(1, num_taps + 1):
            pt = self.get_deployment_point(randomize=True)
            actions.append(BBDeploymentAction(
                action_type=BBActionType.TAP_SCREEN,
                target_norm_pos=pt,
                delay_after=self.tap_delay,
                description=f"Cascade Deploy Reinforcements (Tap {tap_i}/{num_taps})"
            ))

        return actions
