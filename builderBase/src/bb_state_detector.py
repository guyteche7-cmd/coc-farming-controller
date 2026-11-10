"""
Builder Base UI State Detector.
Recognizes all Builder Base 2.0 game screens, active battle stages, and UI buttons.
Dynamically detects troop slot counts across different Builder Hall levels.
"""

from __future__ import annotations
import os
import cv2
import numpy as np
import logging
from enum import Enum
from typing import Dict, Tuple, Optional, List, Any
from pydantic import BaseModel
from builderBase.src.bb_audit_logger import bb_audit

logger = logging.getLogger(__name__)


class BBUIState(Enum):
    UNKNOWN = "UNKNOWN"
    BB_HOME = "BB_HOME"
    BB_START_ATTACK_MODAL = "BB_START_ATTACK_MODAL"
    BB_MATCHMAKING = "BB_MATCHMAKING"
    BB_BATTLE_COUNTDOWN = "BB_BATTLE_COUNTDOWN"   # "Battle starts in: Xs" pre-battle phase
    BB_STAGE1_BATTLE = "BB_STAGE1_BATTLE"
    BB_STAGE2_BATTLE = "BB_STAGE2_BATTLE"
    BB_CONFIRM_DIALOG = "BB_CONFIRM_DIALOG"
    BB_RESULT_SCREEN = "BB_RESULT_SCREEN"


class BBDetectionResult(BaseModel):
    state: BBUIState
    confidence: float
    details: str = ""
    active_troop_slots: List[int] = []


class BBStateDetector:
    """Detects UI states and button locations for Builder Base."""

    DEFAULT_ANCHORS: Dict[str, Tuple[float, float]] = {
        "ATTACK_BUTTON": (0.055, 0.885),
        "FIND_NOW_BUTTON": (0.740, 0.611),
        "MODAL_CLOSE_X": (0.855, 0.167),
        "DEPLOYMENT_SPOT": (0.776, 0.102),
        "HERO_SLOT_0": (0.098, 0.833),
        "SLOT_1": (0.188, 0.833),
        "SLOT_2": (0.265, 0.833),
        "SLOT_3": (0.342, 0.833),
        "SLOT_4": (0.419, 0.833),
        "SLOT_5": (0.496, 0.833),
        "SLOT_6": (0.573, 0.833),
        "SLOT_7": (0.650, 0.833),
        "SLOT_8": (0.727, 0.833),
        "SURRENDER_BUTTON": (0.072, 0.644),
        "END_BATTLE_BUTTON": (0.072, 0.644),
        "CONFIRM_OKAY_BUTTON": (0.594, 0.593),
        "CONFIRM_CANCEL_BUTTON": (0.404, 0.593),
        "RETURN_HOME_BUTTON": (0.501, 0.850),
    }

    SLOT_POSITIONS: Dict[int, Tuple[float, float]] = {
        0: (0.098, 0.833),
        1: (0.188, 0.833),
        2: (0.265, 0.833),
        3: (0.342, 0.833),
        4: (0.419, 0.833),
        5: (0.496, 0.833),
        6: (0.573, 0.833),
        7: (0.650, 0.833),
        8: (0.727, 0.833),
    }

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "ui"))
        self.templates_dir = templates_dir
        self.templates: Dict[str, np.ndarray] = {}
        self.dynamic_anchors: Dict[str, Tuple[float, float]] = dict(self.DEFAULT_ANCHORS)
        self._load_templates()

    def _load_templates(self) -> None:
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return

        for fname in os.listdir(self.templates_dir):
            if fname.lower().endswith(".png"):
                name = os.path.splitext(fname)[0]
                path = os.path.join(self.templates_dir, fname)
                tpl = cv2.imread(path)
                if tpl is not None:
                    self.templates[name] = tpl

    def _match_template_region(
        self,
        frame: np.ndarray,
        template_name: str,
        norm_roi: Tuple[float, float, float, float],
        threshold: float = 0.60
    ) -> Optional[Tuple[float, Tuple[float, float]]]:
        if template_name not in self.templates or frame is None:
            return None

        tpl = self.templates[template_name]
        fh, fw = frame.shape[:2]
        th, tw = tpl.shape[:2]

        # Proportional resolution scaling (templates are standard 1080p height)
        scale = fh / 1080.0
        if abs(scale - 1.0) > 0.04:
            new_w = max(10, int(tw * scale))
            new_h = max(10, int(th * scale))
            tpl = cv2.resize(tpl, (new_w, new_h))
            th, tw = tpl.shape[:2]

        x1 = max(0, int(norm_roi[0] * fw))
        y1 = max(0, int(norm_roi[1] * fh))
        x2 = min(fw, int(norm_roi[2] * fw))
        y2 = min(fh, int(norm_roi[3] * fh))

        roi = frame[y1:y2, x1:x2]
        rh, rw = roi.shape[:2]
        if rh < th or rw < tw:
            fit_scale = min(rh / th, rw / tw) * 0.95
            if fit_scale < 0.25:
                return None
            tpl = cv2.resize(tpl, (0, 0), fx=fit_scale, fy=fit_scale)
            th, tw = tpl.shape[:2]

        res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            match_x = x1 + max_loc[0] + tw / 2
            match_y = y1 + max_loc[1] + th / 2
            return max_val, (match_x / fw, match_y / fh)

        return None

    def detect_active_slots(self, frame: np.ndarray) -> List[int]:
        """Scans the bottom slot bar and returns a list of populated slot indices (1..8)."""
        fh, fw = frame.shape[:2]
        active_slots: List[int] = []

        for slot_idx in range(1, 9):
            nx, ny = self.SLOT_POSITIONS[slot_idx]
            cx, cy = int(nx * fw), int(ny * fh)
            w_box, h_box = int(0.025 * fw), int(0.035 * fh)

            x1 = max(0, cx - w_box)
            y1 = max(0, cy - h_box)
            x2 = min(fw, cx + w_box)
            y2 = min(fh, cy + h_box)

            slot_crop = frame[y1:y2, x1:x2]
            if slot_crop.size == 0:
                continue

            std_bgr = np.std(slot_crop)
            if std_bgr >= 45.0:
                active_slots.append(slot_idx)

        return active_slots

    def detect_ui_state(self, frame: np.ndarray) -> BBDetectionResult:
        """Determines the current Builder Base UI state with high precision."""
        if frame is None or frame.size == 0:
            return BBDetectionResult(state=BBUIState.UNKNOWN, confidence=0.0, details="Empty frame")

        fh, fw = frame.shape[:2]

        # 1. HIGH-PRIORITY: CONFIRMATION DIALOG (Surrender? / End Battle?)
        m_okay = self._match_template_region(frame, "dialog_okay_button", (0.45, 0.45, 0.75, 0.75), threshold=0.70)
        if m_okay:
            score, norm_center = m_okay
            self.dynamic_anchors["CONFIRM_OKAY_BUTTON"] = norm_center
            res = BBDetectionResult(state=BBUIState.BB_CONFIRM_DIALOG, confidence=score, details="Surrender/End Battle confirmation modal detected")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 2. START ATTACK MODAL (Find Now! button on right side of modal)
        m_find = self._match_template_region(frame, "find_now_button", (0.55, 0.45, 0.90, 0.80), threshold=0.70)
        if m_find:
            score, norm_center = m_find
            self.dynamic_anchors["FIND_NOW_BUTTON"] = norm_center
            res = BBDetectionResult(state=BBUIState.BB_START_ATTACK_MODAL, confidence=score, details="'Start Attack' modal detected")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 3. RESULT SCREEN (Return Home button strictly centered at bottom)
        m_ret = self._match_template_region(frame, "return_home_button", (0.40, 0.75, 0.60, 0.98), threshold=0.75)
        if m_ret:
            score, norm_center = m_ret
            self.dynamic_anchors["RETURN_HOME_BUTTON"] = norm_center
            res = BBDetectionResult(state=BBUIState.BB_RESULT_SCREEN, confidence=score, details="Battle Result Screen detected")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 4. MATCHMAKING ("Searching for opponents...")
        m_search = self._match_template_region(frame, "searching_opponents", (0.25, 0.30, 0.75, 0.70), threshold=0.60)
        if m_search:
            score, _ = m_search
            res = BBDetectionResult(state=BBUIState.BB_MATCHMAKING, confidence=score, details="Matchmaking search in progress")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 5. BB HOME VILLAGE (Attack! button in bottom-left)
        m_atk = self._match_template_region(frame, "attack_button", (0.01, 0.75, 0.15, 0.98), threshold=0.70)
        if m_atk:
            score, center = m_atk
            self.dynamic_anchors["ATTACK_BUTTON"] = center
            res = BBDetectionResult(state=BBUIState.BB_HOME, confidence=score, details="Builder Base Home village detected")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 6. PRE-BATTLE COUNTDOWN ("Battle starts in: Xs")
        # Detected by the Boost Army (purple) or Boost Heroes (silver) buttons visible ONLY during preparation
        m_ba = self._match_template_region(frame, "bb_boost_army_pill", (0.05, 0.50, 0.45, 0.80), threshold=0.70)
        m_bh = self._match_template_region(frame, "bb_boost_heroes_pill", (0.20, 0.50, 0.60, 0.80), threshold=0.70)
        if m_ba or m_bh:
            score = max(m_ba[0] if m_ba else 0.0, m_bh[0] if m_bh else 0.0)
            res = BBDetectionResult(state=BBUIState.BB_BATTLE_COUNTDOWN, confidence=score, details="Pre-battle countdown ('Battle starts in: Xs') detected — waiting to deploy")
            bb_audit.log_detection(res.state.name, res.confidence, res.details)
            return res

        # 7. ACTIVE BATTLE (Stage 1 or Stage 2) — only runs if NOT in countdown
        hero_crop = frame[int(0.78 * fh):int(0.95 * fh), int(0.05 * fw):int(0.15 * fw)]
        std_hero = float(np.std(hero_crop)) if hero_crop.size > 0 else 0.0
        active_slots = self.detect_active_slots(frame)

        m_surr = self._match_template_region(frame, "surrender_button", (0.00, 0.50, 0.25, 0.85), threshold=0.60)
        m_end = self._match_template_region(frame, "end_battle_button", (0.00, 0.50, 0.25, 0.85), threshold=0.60)
        m_boost = self._match_template_region(frame, "boost_army_button", (0.00, 0.50, 0.15, 0.85), threshold=0.80)

        is_battle = (m_surr is not None or m_end is not None or m_boost is not None) or (len(active_slots) >= 1 and std_hero >= 35.0)

        if is_battle:
            score = 1.0
            if m_surr:
                self.dynamic_anchors["SURRENDER_BUTTON"] = m_surr[1]
                score = m_surr[0]
            if m_end:
                self.dynamic_anchors["END_BATTLE_BUTTON"] = m_end[1]
                score = m_end[0]

            if 7 in active_slots or 8 in active_slots:
                res = BBDetectionResult(
                    state=BBUIState.BB_STAGE2_BATTLE,
                    confidence=score,
                    details=f"Stage 2 Battle active ({len(active_slots)} slots: {active_slots})",
                    active_troop_slots=active_slots
                )
            else:
                res = BBDetectionResult(
                    state=BBUIState.BB_STAGE1_BATTLE,
                    confidence=score,
                    details=f"Stage 1 Battle active ({len(active_slots)} slots: {active_slots})",
                    active_troop_slots=active_slots
                )
            bb_audit.log_detection(res.state.name, res.confidence, res.details, res.active_troop_slots)
            return res

        return BBDetectionResult(state=BBUIState.UNKNOWN, confidence=0.0, details="No matching UI state")
