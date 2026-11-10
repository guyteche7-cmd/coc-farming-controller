"""
Hybrid UI State Detector (Version 1).
Combines YOLOv8 AI Object Detection (best.pt) with Template Matching and OCR fallbacks
for ultra-reliable UI navigation and automatic self-correction across any screen size.
"""

from __future__ import annotations
import os
import glob
import logging
from typing import Dict, Optional, Tuple, Any, List
import cv2
import numpy as np

from src.state.game_state import UIState, DetectionResult
from src.vision.ocr_engine import OCREngine
from src.vision.ai_detector import AIVisionDetector

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets",
    "ui"
)


class UIStateDetector:
    """Hybrid Perception Engine: YOLOv8 AI + Multi-Scale OpenCV + Deterministic Color Heuristics."""

    def __init__(self, template_dir: Optional[Any] = None, ocr_engine: Optional[OCREngine] = None, use_ai: bool = True):
        # Support positional OCREngine argument
        if isinstance(template_dir, OCREngine):
            ocr_engine = template_dir
            template_dir = None

        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.templates: Dict[str, np.ndarray] = {}
        self.ocr = ocr_engine or OCREngine()
        self.ai = AIVisionDetector() if use_ai else None
        self.dynamic_anchors: Dict[str, Tuple[float, float]] = {}
        self.last_ai_detections: Dict[str, List[Dict[str, Any]]] = {}
        self.last_popup: Optional[Any] = None

        self._load_templates()

    def _load_templates(self) -> None:
        if not os.path.exists(self.template_dir):
            logger.warning(f"Template directory {self.template_dir} does not exist.")
            return

        for filepath in glob.glob(os.path.join(self.template_dir, "*.png")):
            name = os.path.splitext(os.path.basename(filepath))[0]
            img = cv2.imread(filepath)
            if img is not None:
                self.templates[name] = img
        logger.info(f"Loaded {len(self.templates)} visual templates: {sorted(list(self.templates.keys()))}")

    def detect_ui_state(self, frame_bgr: np.ndarray) -> DetectionResult:
        """
        Executes hybrid perception:
        1. YOLOv8 AI Object Detection (Dynamic coordinates & classes)
        2. Multi-Scale Template Matching Fallback
        3. Targeted OCR Fallback
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return DetectionResult(value=UIState.UNKNOWN, confidence=0.0, errors=["Empty frame"])

        h, w, _ = frame_bgr.shape
        if h == 0 or w == 0:
            return DetectionResult(value=UIState.UNKNOWN, confidence=0.0, errors=["Invalid frame dimensions"])

        self.dynamic_anchors.clear()
        self.last_popup = None

        # -------------------------------------------------------------
        # 0. DETERMINISTIC COLOR PASS (Instant, 100% Reliable across any resolution)
        # -------------------------------------------------------------
        # Check Home Village via golden-yellow Battle button in bottom-left
        bl_crop = frame_bgr[int(h * 0.78):int(h * 0.99), int(w * 0.01):int(w * 0.12)]
        if bl_crop.size > 0:
            bl_yellow = (bl_crop[:, :, 2] > 180) & (bl_crop[:, :, 1] > 140) & (bl_crop[:, :, 0] < 120)
            if np.count_nonzero(bl_yellow) / float(bl_crop.shape[0] * bl_crop.shape[1]) >= 0.20:
                self.dynamic_anchors["HOME_ATTACK_BUTTON"] = (0.065, 0.892)
                return DetectionResult(value=UIState.HOME, confidence=0.98)

        # -------------------------------------------------------------
        # 1. AI PERCEPTION PASS (YOLOv8 best.pt)
        # -------------------------------------------------------------
        if self.ai and self.ai.is_ready():
            ai_dets = self.ai.detect(frame_bgr)
            self.last_ai_detections = ai_dets

            # 1. Check Result Screen Return Home (Top Priority for Combat Exit)
            if "return_home" in ai_dets and ai_dets["return_home"]:
                best = max(ai_dets["return_home"], key=lambda x: x["confidence"])
                self.dynamic_anchors["RETURN_HOME_BUTTON"] = best["center_norm"]
                is_defeat = self._match_template_region(frame_bgr, "defeat_banner_v2", (0.30, 0.15, 0.70, 0.45), threshold=0.68) or \
                            self._match_template_region(frame_bgr, "defeat_banner", (0.30, 0.15, 0.70, 0.45), threshold=0.68)
                res_val = UIState.DEFEAT_RESULT if is_defeat else UIState.VICTORY_RESULT
                return DetectionResult(value=res_val, confidence=best["confidence"])

            # 2. Check Surrender / End Battle Confirmation Dialog (Only if verified by modal title / buttons)
            if "surr_conf" in ai_dets and ai_dets["surr_conf"]:
                best = max(ai_dets["surr_conf"], key=lambda x: x["confidence"])
                if best["confidence"] >= 0.50:
                    diag_val = self._validate_confirmation_dialog(frame_bgr)
                    if diag_val is not None:
                        self.dynamic_anchors["CONFIRM_OKAY_BUTTON"] = best["center_norm"]
                        return DetectionResult(value=diag_val, confidence=best["confidence"])
                    else:
                        logger.debug(
                            f"[STATE DETECTOR] Rejected false-positive surr_conf detection at "
                            f"{best['center_norm']} (conf={best['confidence']:.2f}) - no modal dialog found."
                        )
                        if "CONFIRM_OKAY_BUTTON" in self.dynamic_anchors:
                            del self.dynamic_anchors["CONFIRM_OKAY_BUTTON"]

            # 3. Check Attack Menu / Multiplayer (find_btn under Battle card) - Priority over attack_btn
            if "find_btn" in ai_dets and ai_dets["find_btn"]:
                best = max(ai_dets["find_btn"], key=lambda x: x["confidence"])
                self.dynamic_anchors["FIND_A_MATCH_BUTTON"] = best["center_norm"]
                self.dynamic_anchors["FIND_A_MATCH_BATTLE_BUTTON"] = best["center_norm"]
                return DetectionResult(value=UIState.ATTACK_MENU, confidence=best["confidence"])

            # 4. Check My Army Screen (Green Attack! button on bottom-right: norm_x > 0.65, norm_y > 0.75)
            if "attack_btn" in ai_dets and ai_dets["attack_btn"]:
                right_attack_btns = [
                    b for b in ai_dets["attack_btn"]
                    if b["center_norm"][0] > 0.65 and b["center_norm"][1] > 0.75
                ]
                if right_attack_btns:
                    best = max(right_attack_btns, key=lambda x: x["confidence"])
                    self.dynamic_anchors["ARMY_SCREEN_ATTACK_BUTTON"] = best["center_norm"]
                    return DetectionResult(value=UIState.MY_ARMY_SCREEN, confidence=best["confidence"])

            # 5. Check Candidate Battle (nxt_btn strictly in bottom-right corner)
            if "nxt_btn" in ai_dets and ai_dets["nxt_btn"]:
                valid_nxt = [d for d in ai_dets["nxt_btn"] if d["center_norm"][0] >= 0.75 and d["center_norm"][1] >= 0.60]
                if valid_nxt:
                    best = max(valid_nxt, key=lambda x: x["confidence"])
                    self.dynamic_anchors["CANDIDATE_NEXT_BUTTON"] = best["center_norm"]
                    if "end_btn" in ai_dets and ai_dets["end_btn"]:
                        best_end = max(ai_dets["end_btn"], key=lambda x: x["confidence"])
                        self.dynamic_anchors["END_BATTLE_BUTTON"] = best_end["center_norm"]
                    return DetectionResult(value=UIState.CANDIDATE_BATTLE, confidence=best["confidence"])

            # 6. Check Home Attack Button (Bottom-left swords)
            if "attack_btn_home" in ai_dets and ai_dets["attack_btn_home"]:
                bl_dets = [d for d in ai_dets["attack_btn_home"] if d["center_norm"][0] <= 0.11 and d["center_norm"][1] >= 0.80]
                if bl_dets:
                    best = max(bl_dets, key=lambda x: x["confidence"])
                    self.dynamic_anchors["HOME_ATTACK_BUTTON"] = best["center_norm"]
                    return DetectionResult(value=UIState.HOME, confidence=best["confidence"])

            # 7. Check Active Battle vs End Battle/Surrender Confirmation Dialog
            if "end_btn" in ai_dets and ai_dets["end_btn"]:
                valid_nxt = [d for d in ai_dets.get("nxt_btn", []) if d["center_norm"][0] >= 0.75 and d["center_norm"][1] >= 0.60]
                if not valid_nxt:
                    best = max(ai_dets["end_btn"], key=lambda x: x["confidence"])
                    self.dynamic_anchors["END_BATTLE_BUTTON"] = best["center_norm"]
                    self.dynamic_anchors["SURRENDER_BUTTON"] = best["center_norm"]

                    # Check if End Battle / Surrender confirmation dialog is genuinely open on top of battle
                    diag_val = self._validate_confirmation_dialog(frame_bgr)
                    if diag_val is not None:
                        if "surr_conf" in ai_dets and ai_dets["surr_conf"]:
                            best_sc = max(ai_dets["surr_conf"], key=lambda x: x["confidence"])
                            self.dynamic_anchors["CONFIRM_OKAY_BUTTON"] = best_sc["center_norm"]
                        return DetectionResult(value=diag_val, confidence=0.96)

                    return DetectionResult(value=UIState.ACTIVE_BATTLE, confidence=best["confidence"])

        # -------------------------------------------------------------
        # 2. TEMPLATE MATCHING PASS (High-Precision Fallback)
        # -------------------------------------------------------------

        # 0. Check Pick a Reward modal (100% Victory or Mid-battle 40%/65% damage)
        if self._match_template_region(frame_bgr, "pick_reward_win", (0.35, 0.20, 0.65, 0.38), threshold=0.68) or \
           self._match_template_region(frame_bgr, "pick_reward_mid", (0.35, 0.10, 0.65, 0.26), threshold=0.68):
            self.dynamic_anchors["REWARD_CARD_MIDDLE"] = (0.503, 0.547)
            self.dynamic_anchors["REWARD_CARD_LEFT"] = (0.295, 0.547)
            self.dynamic_anchors["REWARD_CARD_RIGHT"] = (0.712, 0.547)
            return DetectionResult(value=UIState.PICK_REWARD, confidence=0.98)

        # A. Dialogs (End Battle? / Surrender?) - High Priority (Strictly Validated)
        diag_state = self._validate_confirmation_dialog(frame_bgr)
        if diag_state is not None:
            return DetectionResult(value=diag_state, confidence=0.95)

        # B. Attack Menu (Multiplayer card Find Match or Multiplayer Tab)
        has_find_match = self._match_template_region(frame_bgr, "find_match_battle_button_v2", (0.05, 0.65, 0.35, 0.88), threshold=0.65) or \
                         self._match_template_region(frame_bgr, "find_match_text_crop_v2", (0.05, 0.65, 0.35, 0.88), threshold=0.65) or \
                         self._match_template_region(frame_bgr, "find_match_battle_button", (0.05, 0.65, 0.35, 0.88), threshold=0.65)
        has_multiplayer_tab = self._match_template_region(frame_bgr, "multiplayer_tab_v2", (0.01, 0.02, 0.25, 0.16), threshold=0.65) or \
                              self._match_template_region(frame_bgr, "multiplayer_tab", (0.01, 0.02, 0.25, 0.16), threshold=0.65)

        if has_find_match or has_multiplayer_tab:
            if "FIND_A_MATCH_BUTTON" not in self.dynamic_anchors:
                self.dynamic_anchors["FIND_A_MATCH_BUTTON"] = (0.173, 0.760)
                self.dynamic_anchors["FIND_A_MATCH_BATTLE_BUTTON"] = (0.173, 0.760)
            return DetectionResult(value=UIState.ATTACK_MENU, confidence=0.96)

        # C. My Army Screen (Green Attack! button OR Beige Battle map button OR My Army tab)
        has_army_attack = self._match_template_region(frame_bgr, "army_screen_attack_button_v2", (0.75, 0.85, 0.99, 0.99), threshold=0.65) or \
                          self._match_template_region(frame_bgr, "army_screen_attack_button", (0.75, 0.80, 0.99, 0.95), threshold=0.65)
        has_army_battle = self._match_template_region(frame_bgr, "army_screen_battle_button_v2", (0.75, 0.82, 0.99, 0.98), threshold=0.65) or \
                          self._match_template_region(frame_bgr, "army_screen_battle_button_1080", (0.75, 0.82, 0.99, 0.98), threshold=0.65)
        has_army_tab = self._match_template_region(frame_bgr, "my_army_tab_v2", (0.02, 0.04, 0.38, 0.16), threshold=0.65) or \
                       self._match_template_region(frame_bgr, "my_army_tab_v2_1080", (0.02, 0.04, 0.38, 0.16), threshold=0.65) or \
                       self._match_template_region(frame_bgr, "my_army_header", (0.02, 0.04, 0.38, 0.16), threshold=0.65)
        has_modal_close = self._match_template_region(frame_bgr, "modal_close_x_v2", (0.92, 0.04, 0.99, 0.16), threshold=0.65) or \
                          self._match_template_region(frame_bgr, "modal_close_x_v2_1080", (0.92, 0.04, 0.99, 0.16), threshold=0.65)

        if has_army_attack or has_army_battle or (has_army_tab and has_modal_close):
            if has_army_battle and "ARMY_SCREEN_BATTLE_BUTTON" not in self.dynamic_anchors:
                self.dynamic_anchors["ARMY_SCREEN_BATTLE_BUTTON"] = (0.886, 0.898)
            if has_army_attack and "ARMY_SCREEN_ATTACK_BUTTON" not in self.dynamic_anchors:
                self.dynamic_anchors["ARMY_SCREEN_ATTACK_BUTTON"] = (0.886, 0.932)
            if has_modal_close and "CLOSE_MODAL_X" not in self.dynamic_anchors:
                self.dynamic_anchors["CLOSE_MODAL_X"] = (0.965, 0.098)
            return DetectionResult(value=UIState.MY_ARMY_SCREEN, confidence=0.96)

        # D. Result Screens (Victory / Defeat)
        has_vic_banner = self._match_template_region(frame_bgr, "victory_banner_v2", (0.30, 0.15, 0.70, 0.45), threshold=0.68) or \
                         self._match_template_region(frame_bgr, "victory_banner", (0.30, 0.15, 0.70, 0.45), threshold=0.68)
        has_def_banner = self._match_template_region(frame_bgr, "defeat_banner_v2", (0.30, 0.15, 0.70, 0.45), threshold=0.68) or \
                         self._match_template_region(frame_bgr, "defeat_banner", (0.30, 0.15, 0.70, 0.45), threshold=0.68)
        has_ret_home = self._match_template_region(frame_bgr, "return_home_button_v2", (0.40, 0.78, 0.60, 0.98), threshold=0.68) or \
                       self._match_template_region(frame_bgr, "return_home_button", (0.40, 0.78, 0.60, 0.98), threshold=0.68)
        if has_vic_banner or (has_ret_home and not has_def_banner):
            return DetectionResult(value=UIState.VICTORY_RESULT, confidence=0.96)
        if has_def_banner:
            return DetectionResult(value=UIState.DEFEAT_RESULT, confidence=0.96)

        # E. Searching for opponents / Clouds screen
        if self._match_template_region(frame_bgr, "searching_opponents_center", (0.28, 0.30, 0.72, 0.70), threshold=0.65) or \
           self._match_template_region(frame_bgr, "clouds_return_home_button", (0.01, 0.75, 0.15, 0.99), threshold=0.68):
            return DetectionResult(value=UIState.MATCHMAKING, confidence=0.94)

        # F. Candidate Battle Screen ("Next" button in bottom-right OR Loot Panel top-left)
        has_next_btn = self._match_template_region(frame_bgr, "next_button_v2", (0.75, 0.60, 0.99, 0.90), threshold=0.65) or \
                       self._match_template_region(frame_bgr, "next_button", (0.80, 0.65, 0.99, 0.99), threshold=0.65)
        has_loot_panel = self._match_template_region(frame_bgr, "loot_gold_row", (0.01, 0.05, 0.18, 0.35), threshold=0.65) or \
                         self._match_template_region(frame_bgr, "loot_elixir_row", (0.01, 0.05, 0.18, 0.35), threshold=0.65)

        br_crop = frame_bgr[int(h * 0.65):int(h * 0.88), int(w * 0.80):int(w * 0.99)]
        has_orange_next = False
        if br_crop.size > 0:
            hsv_br = cv2.cvtColor(br_crop, cv2.COLOR_BGR2HSV)
            orange = cv2.inRange(hsv_br, np.array([10, 140, 140]), np.array([25, 255, 255]))
            has_orange_next = (np.count_nonzero(orange) / float(br_crop.shape[0] * br_crop.shape[1])) >= 0.15

        if has_next_btn or has_loot_panel or has_orange_next:
            if "CANDIDATE_NEXT_BUTTON" not in self.dynamic_anchors:
                self.dynamic_anchors["CANDIDATE_NEXT_BUTTON"] = (0.915, 0.765)
            if "END_BATTLE_BUTTON" not in self.dynamic_anchors:
                self.dynamic_anchors["END_BATTLE_BUTTON"] = (0.065, 0.795)
            return DetectionResult(value=UIState.CANDIDATE_BATTLE, confidence=0.96)

        # G. Active Battle Screen
        if self._match_template_region(frame_bgr, "surrender_button_v2", (0.01, 0.68, 0.16, 0.88), threshold=0.68) or \
           self._match_template_region(frame_bgr, "end_battle_button_v2", (0.01, 0.68, 0.16, 0.88), threshold=0.68) or \
           self._match_template_region(frame_bgr, "surrender_button", (0.01, 0.68, 0.16, 0.88), threshold=0.68) or \
           self._match_template_region(frame_bgr, "end_battle_active_button", (0.01, 0.68, 0.16, 0.88), threshold=0.68) or \
           self._match_template_region(frame_bgr, "overall_damage_panel", (0.80, 0.70, 0.99, 0.90), threshold=0.68):
            return DetectionResult(value=UIState.ACTIVE_BATTLE, confidence=0.92)

        # H. Home Village (Requires yellow Battle button in bottom-left [x: 0.01 - 0.11, y: 0.80 - 0.98])
        has_home_battle_btn = self._match_template_region(frame_bgr, "home_battle_button_v2", (0.01, 0.80, 0.11, 0.98), threshold=0.60) or \
                              self._match_template_region(frame_bgr, "home_battle_button_crop", (0.01, 0.80, 0.11, 0.98), threshold=0.60) or \
                              self._match_template_region(frame_bgr, "home_attack_button", (0.01, 0.80, 0.11, 0.98), threshold=0.65)
        if has_home_battle_btn:
            return DetectionResult(value=UIState.HOME, confidence=0.96)

        # -------------------------------------------------------------
        # 3. FAST COLOR & OCR FALLBACK
        # -------------------------------------------------------------
        gray_full = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        bright_ratio = np.count_nonzero(gray_full > 215) / float(h * w)
        if bright_ratio > 0.65:
            return DetectionResult(value=UIState.MATCHMAKING, confidence=0.88)

        if self.ocr is not None:
            # Check Pick a Reward ribbon via OCR
            center_crop = frame_bgr[int(h * 0.12):int(h * 0.35), int(w * 0.35):int(w * 0.65)]
            c_text, _ = self.ocr.read_text(center_crop)
            if "reward" in c_text.lower() or "pick" in c_text.lower():
                self.dynamic_anchors["REWARD_CARD_MIDDLE"] = (0.503, 0.547)
                self.dynamic_anchors["REWARD_CARD_LEFT"] = (0.295, 0.547)
                self.dynamic_anchors["REWARD_CARD_RIGHT"] = (0.712, 0.547)
                return DetectionResult(value=UIState.PICK_REWARD, confidence=0.95)

            br_crop = frame_bgr[int(h * 0.65):int(h * 0.90), int(w * 0.75):int(w * 0.99)]
            br_text, _ = self.ocr.read_text(br_crop)
            if "next" in br_text.lower():
                return DetectionResult(value=UIState.CANDIDATE_BATTLE, confidence=0.95)

            bl_crop = frame_bgr[int(h * 0.75):int(h * 0.99), int(w * 0.01):int(w * 0.18)]
            bl_text, _ = self.ocr.read_text(bl_crop)
            if "battle" in bl_text.lower() or "attack" in bl_text.lower():
                return DetectionResult(value=UIState.HOME, confidence=0.95)
            if "surrender" in bl_text.lower() or "end" in bl_text.lower():
                return DetectionResult(value=UIState.ACTIVE_BATTLE, confidence=0.95)

        # -------------------------------------------------------------
        # 4. LEVEL-3 OPEN-VOCABULARY VISION & POPUP AWARENESS (Florence-2)
        # -------------------------------------------------------------
        try:
            from src.vision.florence_engine import get_shared_florence_engine
            florence = get_shared_florence_engine()
            popup = florence.detect_popup(frame_bgr)
            if popup is not None:
                self.last_popup = popup
                if popup.dismiss_point:
                    self.dynamic_anchors["POPUP_DISMISS_BUTTON"] = popup.dismiss_point
                    if popup.dismiss_type == "OKAY":
                        self.dynamic_anchors["CONFIRM_OKAY_BUTTON"] = popup.dismiss_point
                    elif popup.dismiss_type == "CANCEL":
                        self.dynamic_anchors["CONFIRM_CANCEL_BUTTON"] = popup.dismiss_point
                    elif popup.dismiss_type == "CLOSE_X":
                        self.dynamic_anchors["CLOSE_MODAL_X"] = popup.dismiss_point
                    elif popup.dismiss_type == "RELOAD":
                        self.dynamic_anchors["POPUP_RELOAD_BUTTON"] = popup.dismiss_point

                state_val = UIState.UNKNOWN if popup.is_dangerous else UIState.POPUP_MODAL
                errs = [f"DANGEROUS_PROMPT: {popup.description}"] if popup.is_dangerous else []
                return DetectionResult(value=state_val, confidence=popup.confidence, errors=errs)
        except Exception as e:
            logger.debug(f"[STATE DETECTOR] Florence-2 popup pass skipped: {e}")

        return DetectionResult(value=UIState.UNKNOWN, confidence=0.0)

    def _match_template_region(
        self,
        frame_bgr: np.ndarray,
        template_name: str,
        norm_bbox: Tuple[float, float, float, float],
        threshold: float = 0.65
    ) -> bool:
        if template_name not in self.templates:
            return False

        tmpl = self.templates[template_name]
        h, w, _ = frame_bgr.shape
        x1 = int(norm_bbox[0] * w)
        y1 = int(norm_bbox[1] * h)
        x2 = int(norm_bbox[2] * w)
        y2 = int(norm_bbox[3] * h)

        crop = frame_bgr[y1:y2, x1:x2]
        if crop.shape[0] < tmpl.shape[0] or crop.shape[1] < tmpl.shape[1]:
            scale_x = crop.shape[1] / float(max(1, tmpl.shape[1]))
            scale_y = crop.shape[0] / float(max(1, tmpl.shape[0]))
            scale = min(scale_x, scale_y)
            if scale <= 0.1:
                return False
            tmpl = cv2.resize(tmpl, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if crop.shape[0] < tmpl.shape[0] or crop.shape[1] < tmpl.shape[1]:
                return False

        res = cv2.matchTemplate(crop, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            # Calculate dynamic center point
            hit_cx = x1 + max_loc[0] + tmpl.shape[1] // 2
            hit_cy = y1 + max_loc[1] + tmpl.shape[0] // 2
            norm_cx = hit_cx / float(w)
            norm_cy = hit_cy / float(h)

            if ("attack" in template_name or "battle" in template_name) and "home" in template_name:
                if norm_cx <= 0.11 and norm_cy >= 0.80:
                    self.dynamic_anchors["HOME_ATTACK_BUTTON"] = (norm_cx, norm_cy)
                else:
                    self.dynamic_anchors["HOME_ATTACK_BUTTON"] = (0.068, 0.880)
            elif "find_match" in template_name:
                self.dynamic_anchors["FIND_A_MATCH_BUTTON"] = (norm_cx, norm_cy)
                self.dynamic_anchors["FIND_A_MATCH_BATTLE_BUTTON"] = (norm_cx, norm_cy)
            elif "army_screen_attack" in template_name:
                self.dynamic_anchors["ARMY_SCREEN_ATTACK_BUTTON"] = (norm_cx, norm_cy)
            elif "next" in template_name:
                self.dynamic_anchors["CANDIDATE_NEXT_BUTTON"] = (norm_cx, norm_cy)
            elif "end_battle" in template_name or "surrender" in template_name:
                self.dynamic_anchors["END_BATTLE_BUTTON"] = (norm_cx, norm_cy)
                self.dynamic_anchors["SURRENDER_BUTTON"] = (norm_cx, norm_cy)
            elif "return_home" in template_name:
                self.dynamic_anchors["RETURN_HOME_BUTTON"] = (norm_cx, norm_cy)
            elif "army_screen_battle" in template_name:
                self.dynamic_anchors["ARMY_SCREEN_BATTLE_BUTTON"] = (norm_cx, norm_cy)
            elif "modal_close_x" in template_name:
                self.dynamic_anchors["CLOSE_MODAL_X"] = (norm_cx, norm_cy)
            elif "dialog_okay" in template_name:
                self.dynamic_anchors["CONFIRM_OKAY_BUTTON"] = (norm_cx, norm_cy)
            elif "dialog_cancel" in template_name:
                self.dynamic_anchors["CONFIRM_CANCEL_BUTTON"] = (norm_cx, norm_cy)

            return True

        return False

    def _validate_confirmation_dialog(self, frame_bgr: np.ndarray) -> Optional[UIState]:
        """
        Validates if an actual in-game confirmation dialog (End Battle? or Surrender?)
        is genuinely open on top of the screen. Prevents base textures, defenses, or walls
        from triggering false-positive dialog confirmations.
        """
        # 1. Check End Battle Title
        is_end = self._match_template_region(frame_bgr, "dialog_end_battle_title_v2", (0.30, 0.18, 0.70, 0.45), threshold=0.62) or \
                 self._match_template_region(frame_bgr, "dialog_end_battle_title", (0.30, 0.18, 0.70, 0.45), threshold=0.62)
        if is_end:
            return UIState.END_BATTLE_DIALOG

        # 2. Check Surrender Title
        is_surrender = self._match_template_region(frame_bgr, "dialog_surrender_title_v2", (0.30, 0.18, 0.70, 0.45), threshold=0.62) or \
                       self._match_template_region(frame_bgr, "dialog_surrender_title", (0.30, 0.18, 0.70, 0.45), threshold=0.62)
        if is_surrender:
            return UIState.SURRENDER_DIALOG

        # 3. Check Cancel Button (Both End Battle and Surrender dialogs have Cancel on bottom-left)
        has_cancel = self._match_template_region(frame_bgr, "dialog_cancel_button_v2", (0.25, 0.45, 0.55, 0.78), threshold=0.62) or \
                     self._match_template_region(frame_bgr, "dialog_cancel_button", (0.25, 0.45, 0.55, 0.78), threshold=0.62)
        if has_cancel:
            # Check if Okay button also matches
            has_okay = self._match_template_region(frame_bgr, "dialog_okay_button_v2", (0.45, 0.45, 0.75, 0.78), threshold=0.62) or \
                       self._match_template_region(frame_bgr, "dialog_okay_button", (0.45, 0.45, 0.75, 0.78), threshold=0.62)
            if has_okay:
                return UIState.END_BATTLE_DIALOG

        # 4. OCR text check across central modal region (0.30, 0.20, 0.70, 0.80)
        h, w = frame_bgr.shape[:2]
        crop_dialog = frame_bgr[int(0.20 * h):int(0.80 * h), int(0.30 * w):int(0.70 * w)]
        if crop_dialog.size > 0 and self.ocr:
            try:
                txt, conf = self.ocr.read_text(crop_dialog)
                txt_lower = txt.lower()
                if any(k in txt_lower for k in ["end battle", "surrender", "give up", "are you sure"]):
                    if "surrender" in txt_lower:
                        return UIState.SURRENDER_DIALOG
                    return UIState.END_BATTLE_DIALOG
            except Exception:
                pass

        return None

