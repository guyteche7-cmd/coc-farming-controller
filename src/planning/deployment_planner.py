"""
Deployment Planner (Targeted Single-Spot Deployment & Adaptive Directional Probing).
Executes smart troop probe deployment beside 'Battle ends in:' on top grass:
1. Selects 1 troop (Slot 0) and drops 1 single test troop at default deploy spot.
2. If screened/blocked, tests adjacent probe positions with 1 troop.
3. Once a location is confirmed, dumps all remaining troops at that exact spot.
4. Deploys Siege (Slot 1) and Heroes (Slots 2-5) with exactly 1 click each (NO multi-clicking heroes).
5. Drops spells (Slot 6).
6. Pauses briefly (1.5s) for march, then activates all Hero Abilities with 1 click each.

Slot Mapping on Army Ribbon (Normalized y=0.900):
- S0 (x=0.106): Slot 0 (Troops / Valkyries)
- S1 (x=0.185): Slot 1 (Siege / Log Launcher / CC)
- S2 (x=0.265): Slot 2 (Hero 1 - Minion Prince / Pet)
- S3 (x=0.345): Slot 3 (Hero 2 - Archer Queen)
- S4 (x=0.425): Slot 4 (Hero 3 - Grand Warden)
- S5 (x=0.505): Slot 5 (Hero 4 - Barbarian King)
- S6 (x=0.585): Slot 6 (Spells)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
from pydantic import BaseModel
from src.state.army_ledger import ArmyLedger

logger = logging.getLogger(__name__)


@dataclass
class ArmySlotLayout:
    troop_slots: List[int]
    siege_slot: Optional[int]
    hero_slots: List[int]
    spell_slots: List[int]
    total_occupied: int
    occupied_slots: List[int]


class ActionType(str, Enum):
    SELECT_SLOT = "SELECT_SLOT"
    DEPLOY_POINT = "DEPLOY_POINT"
    ACTIVATE_ABILITY = "ACTIVATE_ABILITY"
    CLICK_UI = "CLICK_UI"
    WAIT = "WAIT"


class DeploymentAction(BaseModel):
    action_type: ActionType
    target_name: str
    slot_index: Optional[int] = None
    norm_x: float = 0.6055
    norm_y: float = 0.0712
    tap_count: int = 1
    delay_after_sec: float = 0.05
    description: str = ""


class DeploymentPlanner:
    """Universal direct single-point deployment planner with adaptive directional probing."""

    # Precise slot center coordinates from real LDPlayer screenshots (Supports up to 9 slots)
    SLOT_X_COORDINATES = [0.106, 0.185, 0.265, 0.345, 0.425, 0.505, 0.585, 0.665, 0.745]
    RIBBON_Y = 0.900

    # Primary target deploy point from user screenshot (Right of 'Battle ends in:' on top grass)
    TARGET_DEPLOY_X = 0.6055
    TARGET_DEPLOY_Y = 0.0712

    # Directional search probe points to test if default spot is screened/blocked
    PROBE_POINTS = [
        (0.6055, 0.0712),  # 1. Default marked spot beside "Battle ends in:"
        (0.6300, 0.0712),  # 2. Slightly right along top grass
        (0.6550, 0.0712),  # 3. Further right along open grass
        (0.5800, 0.0712),  # 4. Slightly left along top grass
        (0.6055, 0.0450),  # 5. Slightly up towards outer edge
        (0.6300, 0.0450),  # 6. Shift right and up
    ]

    # 11 Precise Earthquake Spell targets marked across the base in user screenshot
    EARTHQUAKE_TARGET_POINTS = [
        (0.5078, 0.2092),  # 1. Top TH / Inner top compartment
        (0.5373, 0.2445),  # 2. Top-right core
        (0.4800, 0.2957),  # 3. Top-left core
        (0.5152, 0.3273),  # 4. Center core / TH gate
        (0.6421, 0.3554),  # 5. Mid-right compartment
        (0.5689, 0.3885),  # 6. Right core / Inferno
        (0.3936, 0.3907),  # 7. Left core / Eagle / X-Bow
        (0.4805, 0.4174),  # 8. Dead center base core
        (0.3282, 0.4312),  # 9. Mid-left compartment
        (0.5610, 0.4951),  # 10. Bottom-right core
        (0.4653, 0.5036),  # 11. Bottom-center core
    ]

    def __init__(
        self,
        edge: str = "top",
        tap_delay: float = 0.035,
        hero_delay: float = 0.10,
        spell_delay: float = 0.05
    ):
        self.edge = "top"
        self.tap_delay = tap_delay
        self.hero_delay = hero_delay
        self.spell_delay = spell_delay

    def get_randomized_spell_points(self) -> List[Tuple[float, float]]:
        """Returns the 11 earthquake spell target points in randomized/shuffled order with micro-jitter."""
        import random
        pts = list(self.EARTHQUAKE_TARGET_POINTS)
        random.shuffle(pts)
        randomized = []
        for x, y in pts:
            # Apply subtle +/- 0.005 micro-jitter for human-like natural clicks
            jx = max(0.20, min(0.80, x + random.uniform(-0.005, 0.005)))
            jy = max(0.15, min(0.65, y + random.uniform(-0.005, 0.005)))
            randomized.append((jx, jy))
        return randomized

    def detect_army_slots(self, frame_bgr=None, configured_hero_count: int = -1, deploy_siege: bool = True) -> ArmySlotLayout:
        """
        Dynamically inspects the bottom army ribbon to determine occupied slots and assigns:
        - Troop slot(s): Contiguous leading slots with quantity count badges (e.g. [0] or [0, 1]...)
        - Siege slot: First slot between troops and heroes (if present and deploy_siege is True)
        - Hero slots: Middle slots without count badges (respecting configured_hero_count if > 0)
        - Spell slots: Trailing slots with quantity count badges at the right of the ribbon
        """
        import numpy as np

        occupied = []
        if frame_bgr is not None and frame_bgr.size > 0:
            h, w = frame_bgr.shape[:2]
            for idx, nx in enumerate(self.SLOT_X_COORDINATES):
                cx = int(nx * w)
                x1, x2 = max(0, int((nx - 0.030) * w)), min(w, int((nx + 0.030) * w))
                y1, y2 = max(0, int(0.835 * h)), min(h, int(0.975 * h))
                crop = frame_bgr[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                mean_v = float(np.mean(crop))
                std_v = float(np.std(crop))
                b_mean = float(np.mean(crop[:, :, 0]))
                g_mean = float(np.mean(crop[:, :, 1]))
                # Empty slots in Clash of Clans have transparent dashed borders where base grass shines through
                is_grass = (g_mean - b_mean > 16.0)
                if not is_grass and (mean_v > 75.0 or (mean_v > 55.0 and std_v > 20.0)):
                    occupied.append(idx)

        # Take contiguous sequence of occupied slots starting from 0
        contiguous = []
        for i in range(len(self.SLOT_X_COORDINATES)):
            if i in occupied:
                contiguous.append(i)
            else:
                break

        total_occ = len(contiguous)
        if total_occ == 0:
            total_occ = 6 if configured_hero_count == 2 else 7
            contiguous = list(range(total_occ))

        # 2. Read quantity badge for each contiguous slot
        slot_counts = {}
        has_badge = {}
        for s in contiguous:
            cnt = self.read_slot_unit_count(frame_bgr, s) if frame_bgr is not None else None
            slot_counts[s] = cnt
            has_badge[s] = (cnt is not None and cnt > 0)

        # 3. Dynamic multi-unit partition:
        # In Clash of Clans, the deployment ribbon ordering is invariant:
        # [Troops (1..N)] -> [Siege Machine (0..1)] -> [Heroes (0..5)] -> [Spells (1..M)]

        # Trailing slots with count badge are Spells (e.g. Slot 5 Earthquake)
        spell_slots = []
        for s in reversed(contiguous):
            if has_badge.get(s, False):
                spell_slots.append(s)
            else:
                break
        spell_slots.reverse()

        num_spells = len(spell_slots) if spell_slots else 1
        expected_heroes = configured_hero_count if configured_hero_count > 0 else 4
        expected_siege = 1 if deploy_siege else 0

        if configured_hero_count > 0 and total_occ >= expected_heroes + expected_siege + 1:
            # Deterministic partition based on invariant order and configured hero/siege count
            troop_end = max(1, total_occ - num_spells - expected_heroes - expected_siege)
            troop_slots = list(range(0, troop_end))
            siege_slot = (troop_slots[-1] + 1) if expected_siege else None
            hero_start = (siege_slot + 1) if siege_slot is not None else (troop_slots[-1] + 1)
            hero_end = min(total_occ - num_spells, hero_start + expected_heroes)
            hero_slots = list(range(hero_start, hero_end))
            spell_slots = list(range(hero_end, total_occ))
        else:
            # Auto hero count: Leading slots with badge (or slot 0) are Troops
            troop_slots = []
            for s in contiguous:
                if has_badge.get(s, False) or s == 0:
                    troop_slots.append(s)
                else:
                    break

            if not troop_slots and total_occ > 0:
                troop_slots = [0]

            first_non_troop = len(troop_slots)
            last_middle = (spell_slots[0] - 1) if spell_slots else (total_occ - 1)
            middle_slots = [s for s in range(first_non_troop, last_middle + 1)]

            if not spell_slots and middle_slots:
                if len(middle_slots) > expected_heroes + expected_siege:
                    spell_slots = [middle_slots.pop()]

            siege_slot = None
            hero_slots = []
            if deploy_siege and middle_slots:
                siege_slot = middle_slots[0]
                hero_slots = middle_slots[1:]
            else:
                hero_slots = list(middle_slots)

            if configured_hero_count > 0 and len(hero_slots) > configured_hero_count:
                hero_slots = hero_slots[:configured_hero_count]

        # Trailing unassigned slots are spells
        assigned = set(troop_slots)
        if siege_slot is not None:
            assigned.add(siege_slot)
        for h in hero_slots:
            assigned.add(h)
        for sp in spell_slots:
            assigned.add(sp)

        unassigned = [s for s in contiguous if s not in assigned]
        if unassigned:
            for u in unassigned:
                if u > (hero_slots[-1] if hero_slots else (siege_slot if siege_slot is not None else troop_slots[-1])):
                    spell_slots.append(u)

        logger.info(
            f"[ARMY LAYOUT] Detected {total_occ} occupied slots -> "
            f"Troops={troop_slots}, Siege={siege_slot}, Heroes={hero_slots} ({len(hero_slots)} heroes), "
            f"Spells={spell_slots} (Configured hero count: {'Auto' if configured_hero_count < 0 else configured_hero_count})"
        )

        return ArmySlotLayout(
            troop_slots=troop_slots,
            siege_slot=siege_slot,
            hero_slots=hero_slots,
            spell_slots=spell_slots,
            total_occupied=total_occ,
            occupied_slots=contiguous
        )


    @staticmethod
    def is_slot_greyed_out(frame_bgr, slot_x: float, ribbon_y: float = 0.890) -> bool:
        """
        Determines if a unit/hero/spell slot is depleted/greyed out by analyzing color saturation and variance.
        Active/Available slot: High saturation (color), high difference between color channels.
        Depleted/Greyed-out slot: Low saturation (monochrome grey), near-zero difference between color channels.
        """
        import cv2
        import numpy as np

        if frame_bgr is None or frame_bgr.size == 0:
            return True
        h, w, _ = frame_bgr.shape
        cx = int(slot_x * w)
        cy = int(ribbon_y * h)

        half_w = int(0.022 * w)
        half_h = int(0.035 * h)

        x1, x2 = max(0, cx - half_w), min(w, cx + half_w)
        y1, y2 = max(0, cy - half_h), min(h, cy + half_h)

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return True

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mean_sat = float(np.mean(hsv[:, :, 1]))

        b, g, r = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
        color_diff = float(np.mean(np.abs(r.astype(float) - g.astype(float)) + np.abs(g.astype(float) - b.astype(float))))

        # Greyed out means low saturation (< 40) and minimal color variance (< 20)
        return mean_sat < 40.0 and color_diff < 20.0

    def read_slot_unit_count(self, frame_bgr, slot_idx: int) -> Optional[int]:
        """
        Reads the unit quantity badge (e.g. 'x42' -> 42) for a given slot index on the bottom ribbon.
        Uses OCR on the top-right badge region of the slot card.
        """
        import re
        import cv2
        import numpy as np
        if frame_bgr is None or frame_bgr.size == 0 or slot_idx < 0 or slot_idx >= len(self.SLOT_X_COORDINATES):
            return None

        h, w = frame_bgr.shape[:2]
        nx = self.SLOT_X_COORDINATES[slot_idx]
        # Precise top-right badge region of the card
        x1 = max(0, int((nx - 0.005) * w))
        x2 = min(w, int((nx + 0.040) * w))
        y1 = max(0, int(0.825 * h))
        y2 = min(h, int(0.875 * h))

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        try:
            from src.vision.ocr_engine import get_shared_paddle_ocr_engine
            ocr = get_shared_paddle_ocr_engine()
            # Upscale 3x for small text recognition
            scaled = cv2.resize(crop, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

            candidates = []
            for th in [170, 150, 190]:
                _, thresh = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
                # Ensure 3-channel for all OCR backends
                thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                candidates.append(thresh_bgr)
            candidates.append(scaled)

            for cand in candidates:
                # Use read_words to bypass button heuristic fallbacks ("end battle", "next")
                words = ocr.read_words(cand, min_conf=0.30)
                if words:
                    for item in words:
                        txt = item.get("text", "").strip()
                        m = re.search(r"[xX]?\s*(\d+)", txt)
                        if m:
                            val = int(m.group(1))
                            conf = item.get("confidence", 0.0)
                            logger.info(f"[DEPLOYMENT PLANNER] Read Slot {slot_idx} unit count: {val} (raw='{txt}', conf={conf:.2f})")
                            return val
        except Exception as e:
            logger.debug(f"[DEPLOYMENT PLANNER] Failed to read badge for slot {slot_idx}: {e}")

        return None

    def generate_deselect_action(self, empty_slot_idx: int = 0) -> DeploymentAction:
        """
        Deselects the currently active ribbon slot (e.g. Hero) by tapping a depleted slot or ribbon margin,
        preventing inadvertent hero deployment clicks during post-deployment battle observation.
        """
        norm_x = self.SLOT_X_COORDINATES[min(empty_slot_idx, len(self.SLOT_X_COORDINATES) - 1)]
        return DeploymentAction(
            action_type=ActionType.CLICK_UI,
            target_name=f"Deselect Active Ribbon Slot (via Slot {empty_slot_idx})",
            slot_index=empty_slot_idx,
            norm_x=norm_x,
            norm_y=self.RIBBON_Y,
            tap_count=1,
            delay_after_sec=0.08,
            description=f"Click depleted slot {empty_slot_idx} to deselect any active hero on ribbon"
        )

    def get_probe_points(self) -> List[Tuple[float, float]]:
        """Returns ordered list of candidate deployment coordinates to probe with 1 single troop."""
        return list(self.PROBE_POINTS)

    def generate_slot_select_action(self, slot_idx: int) -> DeploymentAction:
        """Generates action to select a specific unit slot on the bottom army ribbon."""
        norm_x = self.SLOT_X_COORDINATES[min(slot_idx, len(self.SLOT_X_COORDINATES) - 1)]
        return DeploymentAction(
            action_type=ActionType.SELECT_SLOT,
            target_name=f"Army Slot {slot_idx}",
            slot_index=slot_idx,
            norm_x=norm_x,
            norm_y=self.RIBBON_Y,
            delay_after_sec=0.12,
            description=f"Select Army Slot {slot_idx} on ribbon"
        )

    def generate_single_troop_probe_action(self, norm_x: float, norm_y: float) -> DeploymentAction:
        """Generates 1 single tap action to test if troop drops successfully at (norm_x, norm_y)."""
        return DeploymentAction(
            action_type=ActionType.DEPLOY_POINT,
            target_name="Probe 1 Troop",
            slot_index=0,
            norm_x=norm_x,
            norm_y=norm_y,
            tap_count=1,
            delay_after_sec=0.25,
            description=f"Drop 1 test troop at ({norm_x:.3f}, {norm_y:.3f}) to verify deployment"
        )

    def generate_full_deployment_plan(
        self,
        confirmed_x: float,
        confirmed_y: float,
        troop_tap_count: int = 18
    ) -> List[DeploymentAction]:
        """
        Generates clean full deployment at confirmed coordinates:
        - Slot 0 (Troops): Rapid clicks (troop_tap_count) to empty troop stack
        - Slot 1 (Siege): 1 click to select + 1 click to deploy
        - Slots 2-5 (Heroes): For each hero, 1 click to select + 1 click to deploy (NO multi-clicking!)
        - Slot 6 (Spells): 1 click to select + 2 clicks to cast
        - Pause: 1.5s for heroes to march
        - Hero Abilities (Slots 2-5): 1 click on each hero slot on ribbon to activate ability
        """
        plan: List[DeploymentAction] = []

        # -------------------------------------------------------------
        # 1. SLOT 0: DUMP REMAINING TROOPS AT CONFIRMED SPOT
        # -------------------------------------------------------------
        plan.append(DeploymentAction(
            action_type=ActionType.SELECT_SLOT,
            target_name="Troops (Slot 0)",
            slot_index=0,
            norm_x=self.SLOT_X_COORDINATES[0],
            norm_y=self.RIBBON_Y,
            delay_after_sec=0.10,
            description="Select regular troops (Slot 0)"
        ))
        plan.append(DeploymentAction(
            action_type=ActionType.DEPLOY_POINT,
            target_name="Dump Troops",
            slot_index=0,
            norm_x=confirmed_x,
            norm_y=confirmed_y,
            tap_count=troop_tap_count,
            delay_after_sec=self.tap_delay,
            description=f"Deploy all remaining troops ({troop_tap_count} taps) at ({confirmed_x:.3f}, {confirmed_y:.3f})"
        ))

        # -------------------------------------------------------------
        # 2. SLOT 1: SIEGE MACHINE / CLAN CASTLE (1 CLICK TO DEPLOY)
        # -------------------------------------------------------------
        plan.append(DeploymentAction(
            action_type=ActionType.SELECT_SLOT,
            target_name="Siege Machine (Slot 1)",
            slot_index=1,
            norm_x=self.SLOT_X_COORDINATES[1],
            norm_y=self.RIBBON_Y,
            delay_after_sec=0.10,
            description="Select Siege Machine (Slot 1)"
        ))
        plan.append(DeploymentAction(
            action_type=ActionType.DEPLOY_POINT,
            target_name="Deploy Siege",
            slot_index=1,
            norm_x=confirmed_x,
            norm_y=confirmed_y,
            tap_count=1,
            delay_after_sec=0.10,
            description=f"Deploy Siege Machine (1 tap) at ({confirmed_x:.3f}, {confirmed_y:.3f})"
        ))

        # -------------------------------------------------------------
        # 3. SLOTS 2-5: HEROES (1 CLICK TO SELECT, 1 CLICK TO DEPLOY)
        # -------------------------------------------------------------
        hero_names = ["Hero 1 (Minion Prince)", "Hero 2 (Archer Queen)", "Hero 3 (Grand Warden)", "Hero 4 (Barbarian King)"]
        for idx, slot_idx in enumerate([2, 3, 4, 5]):
            h_name = hero_names[idx] if idx < len(hero_names) else f"Hero Slot {slot_idx}"
            # 1 click to select hero
            plan.append(DeploymentAction(
                action_type=ActionType.SELECT_SLOT,
                target_name=h_name,
                slot_index=slot_idx,
                norm_x=self.SLOT_X_COORDINATES[slot_idx],
                norm_y=self.RIBBON_Y,
                delay_after_sec=0.10,
                description=f"Select {h_name} on ribbon"
            ))
            # 1 click to deploy hero
            plan.append(DeploymentAction(
                action_type=ActionType.DEPLOY_POINT,
                target_name=f"Deploy {h_name}",
                slot_index=slot_idx,
                norm_x=confirmed_x,
                norm_y=confirmed_y,
                tap_count=1,
                delay_after_sec=self.hero_delay,
                description=f"Deploy {h_name} (1 tap) at ({confirmed_x:.3f}, {confirmed_y:.3f})"
            ))

        # -------------------------------------------------------------
        # 4. SLOT 6: SPELLS
        # -------------------------------------------------------------
        plan.append(DeploymentAction(
            action_type=ActionType.SELECT_SLOT,
            target_name="Spells (Slot 6)",
            slot_index=6,
            norm_x=self.SLOT_X_COORDINATES[6],
            norm_y=self.RIBBON_Y,
            delay_after_sec=0.10,
            description="Select Spells (Slot 6)"
        ))
        plan.append(DeploymentAction(
            action_type=ActionType.DEPLOY_POINT,
            target_name="Cast Spells",
            slot_index=6,
            norm_x=confirmed_x,
            norm_y=confirmed_y,
            tap_count=2,
            delay_after_sec=self.spell_delay,
            description=f"Cast Spells (2 taps) at ({confirmed_x:.3f}, {confirmed_y:.3f})"
        ))

        # -------------------------------------------------------------
        # 5. MARCH PAUSE (1.5s) BEFORE TRIGGERING HERO ABILITIES
        # -------------------------------------------------------------
        plan.append(DeploymentAction(
            action_type=ActionType.WAIT,
            target_name="March Pause",
            delay_after_sec=1.5,
            description="Wait 1.5s for heroes and troops to march into base"
        ))

        # -------------------------------------------------------------
        # 6. ACTIVATE HERO ABILITIES (1 CLICK PER HERO ON RIBBON)
        # -------------------------------------------------------------
        for idx, slot_idx in enumerate([2, 3, 4, 5]):
            h_name = hero_names[idx] if idx < len(hero_names) else f"Hero Slot {slot_idx}"
            plan.append(DeploymentAction(
                action_type=ActionType.ACTIVATE_ABILITY,
                target_name=f"Ability: {h_name}",
                slot_index=slot_idx,
                norm_x=self.SLOT_X_COORDINATES[slot_idx],
                norm_y=self.RIBBON_Y,
                tap_count=1,
                delay_after_sec=0.15,
                description=f"Click Hero Slot {slot_idx} (1 tap) to trigger ability for {h_name}"
            ))

        return plan

    def generate_plan(self, ledger: ArmyLedger) -> List[DeploymentAction]:
        """Legacy / fallback plan generator using primary target deploy spot."""
        return self.generate_full_deployment_plan(self.TARGET_DEPLOY_X, self.TARGET_DEPLOY_Y)

    def generate_recovery_plan(self, ledger: ArmyLedger, hero_slots: Optional[List[int]] = None) -> List[DeploymentAction]:
        """Triggers Hero abilities during combat monitoring if damage stagnates (1 click per hero)."""
        recovery_actions: List[DeploymentAction] = []
        target_slots = hero_slots if (hero_slots is not None and len(hero_slots) > 0) else [2, 3]
        for slot_idx in target_slots:
            if slot_idx >= len(self.SLOT_X_COORDINATES):
                continue
            recovery_actions.append(DeploymentAction(
                action_type=ActionType.ACTIVATE_ABILITY,
                target_name=f"Hero Ability {slot_idx}",
                slot_index=slot_idx,
                norm_x=self.SLOT_X_COORDINATES[slot_idx],
                norm_y=self.RIBBON_Y,
                tap_count=1,
                delay_after_sec=0.12,
                description=f"Trigger Hero Ability on Slot {slot_idx}"
            ))
        # Deselect after recovery ability triggers to prevent any hero from staying active
        recovery_actions.append(self.generate_deselect_action(empty_slot_idx=0))
        return recovery_actions

