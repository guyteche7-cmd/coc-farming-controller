"""
Multimodal Vision-Language Model (VLM) Escalation & Complex Reasoning Engine.

Part of the 4-Tier Perception Hierarchy for Clash of Clans:
- Tier 1: Deterministic Pixel Glyph Matching (Numbers, Loot, Timers)
- Tier 2: PaddleOCR PP-OCRv4 (Text, Names, Clan Tags, Buttons)
- Tier 3: Microsoft Florence-2 (Open-Vocabulary Grounding & Unknown Popups)
- Tier 4: Multimodal Reasoning (Pluggable Cloud LLM / Self-Contained Local Fallback)

MODULAR SEPARATION NOTE:
This module is strictly decoupled from external cloud LLMs.
External LLM implementations (e.g. Google Gemini API) reside exclusively in the
optional plugin directory `src/extensions/external_llm/`.
If that directory is removed or disabled, this engine operates 100% locally with
zero broken imports and zero errors.
"""

from __future__ import annotations
import os
import time
import json
import hashlib
import logging
from enum import Enum
from typing import Optional, Tuple, Any, Dict, List
import cv2
import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global singleton instance
_SHARED_VLM_ENGINE: Optional[MultimodalVLMEngine] = None


class VLMActionType(str, Enum):
    """Categorization of actions recommended by the Multimodal VLM."""
    CLICK = "CLICK"
    DISMISS_POPUP = "DISMISS_POPUP"
    WAIT = "WAIT"
    PAUSE = "PAUSE"
    RESTART_EMULATOR = "RESTART_EMULATOR"
    UNKNOWN = "UNKNOWN"


class VLMReasoningResult(BaseModel):
    """Structured reasoning output from the Multimodal Vision-Language Model."""
    scene_summary: str = Field(description="High-level description of what is currently on the screen.")
    screen_classification: str = Field(description="Classified screen type, e.g. HOME_VILLAGE, ACTIVE_BATTLE, POPUP_MODAL, MAINTENANCE, BAN_WARNING, REWARD_CHOICE, UNKNOWN.")
    is_stuck_or_deadlocked: bool = Field(default=False, description="True if the current screen represents a stuck or deadlocked state.")
    is_dangerous: bool = Field(default=False, description="True if prompt asks to spend Gems, make purchases, or confirm irreversible actions.")
    suggested_action: VLMActionType = Field(default=VLMActionType.WAIT, description="Recommended next action for the controller.")
    target_coordinates: Optional[List[float]] = Field(default=None, description="Normalized [norm_x, norm_y] [0.0 to 1.0] coordinates to click if suggested_action is CLICK or DISMISS_POPUP.")
    target_element_description: str = Field(default="", description="Description of the button or element to interact with.")
    confidence: float = Field(default=0.85, description="Confidence score of the reasoning analysis.")
    reasoning: str = Field(default="", description="Detailed step-by-step reasoning explaining why this action is safe and optimal.")
    source_model: str = Field(default="local_reasoning_fallback", description="Model name that generated the reasoning.")


class MultimodalVLMEngine:
    """
    Tier 4 Reasoning & Escalation Engine.
    Coordinates between optional external Cloud VLM plugins and self-contained local vision heuristics.
    """

    MIN_CALL_INTERVAL_SECONDS = 12.0  # Rate limit / debounce between reasoning calls

    def __init__(self, api_key: Optional[str] = None, enable_external: bool = True):
        self.enable_external = enable_external
        self.last_call_time: float = 0.0
        self.last_frame_hash: Optional[str] = None
        self.last_result: Optional[VLMReasoningResult] = None
        self.external_provider: Optional[Any] = None

        if self.enable_external:
            self.external_provider = self._load_external_provider(api_key=api_key)

    @staticmethod
    def _load_external_provider(api_key: Optional[str] = None) -> Optional[Any]:
        """Dynamically and safely loads external LLM plugin without hard dependencies."""
        try:
            from src.extensions.external_llm.gemini_provider import GeminiVLMProvider
            provider = GeminiVLMProvider(api_key=api_key)
            logger.info("[VLM ENGINE] External Cloud LLM plugin successfully loaded.")
            return provider
        except (ImportError, ModuleNotFoundError):
            logger.info("[VLM ENGINE] External LLM extension is not present. Operating in 100% self-contained local mode.")
            return None
        except Exception as e:
            logger.warning(f"[VLM ENGINE] External LLM extension failed to load: {e}. Running in local mode.")
            return None

    def is_available(self) -> bool:
        """Returns True if the engine is ready to perform reasoning."""
        return True

    def has_external_llm(self) -> bool:
        """Returns True if an external Cloud LLM provider is installed and ready."""
        return self.external_provider is not None and self.external_provider.is_available()

    def set_external_llm_enabled(self, enabled: bool) -> None:
        """Toggles external Cloud LLM usage."""
        self.enable_external = enabled
        if enabled and self.external_provider is None:
            self.external_provider = self._load_external_provider()

    def set_api_key(self, api_key: str) -> bool:
        """Updates the external provider API key if installed."""
        if self.external_provider is None:
            self.external_provider = self._load_external_provider(api_key=api_key)
        if self.external_provider is not None:
            return self.external_provider.set_api_key(api_key)
        return False

    def _compute_frame_hash(self, frame_bgr: np.ndarray) -> str:
        """Computes a fast perceptual MD5 hash of a downscaled frame for caching."""
        small = cv2.resize(frame_bgr, (128, 72), interpolation=cv2.INTER_AREA)
        return hashlib.md5(small.tobytes()).hexdigest()

    def analyze_screen(
        self,
        frame_bgr: np.ndarray,
        context_hint: str = "",
        force: bool = False
    ) -> VLMReasoningResult:
        """
        Performs multimodal visual reasoning on the game screen.
        If an external Cloud LLM is present and enabled, delegates to it.
        Otherwise, runs the 100% local self-contained Florence-2/OCR fallback.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return VLMReasoningResult(
                scene_summary="Invalid or empty screen frame",
                screen_classification="UNKNOWN",
                is_stuck_or_deadlocked=True,
                is_dangerous=False,
                suggested_action=VLMActionType.WAIT,
                reasoning="Screen frame contains no pixel data.",
                source_model="system"
            )

        now = time.time()
        frame_hash = self._compute_frame_hash(frame_bgr)

        # Cache check: if identical screen and called within rate limit, return cached reasoning
        if not force and frame_hash == self.last_frame_hash and (now - self.last_call_time) < self.MIN_CALL_INTERVAL_SECONDS:
            if self.last_result is not None:
                logger.debug("[VLM ENGINE] Returning cached reasoning (screen state unchanged).")
                return self.last_result

        # Rate limiting guard
        if not force and (now - self.last_call_time) < self.MIN_CALL_INTERVAL_SECONDS:
            time_remaining = self.MIN_CALL_INTERVAL_SECONDS - (now - self.last_call_time)
            logger.debug(f"[VLM ENGINE] Rate limit active ({time_remaining:.1f}s remaining). Using local reasoning fallback.")
            return self._local_vlm_fallback(frame_bgr, context_hint=context_hint)

        # -------------------------------------------------------------
        # Tier 4A: Optional External Cloud LLM Plugin
        # -------------------------------------------------------------
        if self.enable_external and self.external_provider and self.external_provider.is_available():
            try:
                prompt = (
                    "You are an expert autonomous Clash of Clans player and computer vision navigation engine.\n"
                    "Analyze this 1920x1080 game frame running on an Android emulator.\n"
                    f"Context: {context_hint or 'The bot encountered an unhandled screen state and escalated to Tier 4 VLM.'}\n\n"
                    "Evaluate:\n"
                    "1. What is the current screen or modal dialog?\n"
                    "2. Is the bot stuck, deadlocked, or facing an error, maintenance, or update message?\n"
                    "3. CRITICAL SAFETY GUARD: Does this prompt request spending Gems, purchasing resources with currency, "
                    "or confirming irreversible changes? If yes, set is_dangerous = True and suggest PAUSE.\n"
                    "4. If a safe button exists to dismiss the dialog or continue (e.g. Reload Game, Okay, Close 'X', Cancel), "
                    "provide its normalized coordinates (norm_x, norm_y) where 0.0 <= norm_x, norm_y <= 1.0.\n"
                    "5. Provide a clear chain-of-thought in reasoning."
                )

                raw_json = self.external_provider.query_multimodal(
                    frame_bgr=frame_bgr,
                    prompt=prompt,
                    response_schema=VLMReasoningResult
                )

                if raw_json:
                    parsed = VLMReasoningResult.model_validate_json(raw_json)
                    parsed.source_model = getattr(self.external_provider, "model_name", "external-llm")
                    if parsed.is_dangerous:
                        parsed.suggested_action = VLMActionType.PAUSE

                    self.last_call_time = now
                    self.last_frame_hash = frame_hash
                    self.last_result = parsed
                    logger.info(f"[VLM ENGINE] External Cloud VLM reasoning: {parsed.screen_classification} -> {parsed.suggested_action}")
                    return parsed
            except Exception as e:
                logger.warning(f"[VLM ENGINE] External LLM query failed: {e}. Falling back to local mode.")

        # -------------------------------------------------------------
        # Tier 4B: Self-Contained Local VLM Fallback (Florence-2 + PP-OCR)
        # -------------------------------------------------------------
        local_res = self._local_vlm_fallback(frame_bgr, context_hint=context_hint)
        self.last_call_time = now
        self.last_frame_hash = frame_hash
        self.last_result = local_res
        return local_res

    def _local_vlm_fallback(self, frame_bgr: np.ndarray, context_hint: str = "") -> VLMReasoningResult:
        """
        Resilient local vision-language reasoning engine using Florence-2 dense captioning,
        PaddleOCR lexical analysis, and geometric heuristics. Runs completely offline on Windows CPU.
        """
        from src.vision.florence_engine import get_shared_florence_engine
        from src.vision.ocr_engine import get_shared_paddle_ocr_engine

        florence = get_shared_florence_engine()
        ocr = get_shared_paddle_ocr_engine()

        # 1. Florence-2 scene caption
        caption = florence.describe_scene(frame_bgr)
        # 2. Extract visible text words
        words = ocr.read_words(frame_bgr)
        text_content = " ".join([w["text"] for w in words]).lower()

        # 3. Check for dangerous gem spending prompts
        is_dangerous = False
        if "gem" in text_content and any(k in text_content for k in ("spend", "buy", "cost", "finish", "now", "confirm")):
            is_dangerous = True

        # 4. Check for error or reload states
        is_reload = "reload" in text_content or "out of sync" in text_content or "connection lost" in text_content
        is_maintenance = "maintenance" in text_content or "break" in text_content
        is_banned = "banned" in text_content or "suspended" in text_content

        # 5. Check for modal close button
        close_pt = florence._find_modal_close_cross(frame_bgr)

        # Formulate reasoning decision
        if is_banned:
            return VLMReasoningResult(
                scene_summary=f"Account warning or ban detected: {caption}",
                screen_classification="BAN_WARNING",
                is_stuck_or_deadlocked=True,
                is_dangerous=True,
                suggested_action=VLMActionType.PAUSE,
                reasoning="Account suspension or ban message detected. Pausing bot immediately to protect user account.",
                source_model="local_florence_fallback"
            )

        if is_dangerous:
            cancel_coords = None
            for w_item in words:
                if "cancel" in w_item["text"].lower():
                    h, w = frame_bgr.shape[:2]
                    cx, cy = w_item["center"]
                    cancel_coords = [float(cx / float(w)), float(cy / float(h))]
                    break

            return VLMReasoningResult(
                scene_summary=f"Gem spending or resource purchase prompt: {caption}",
                screen_classification="GEM_SPEND_PROMPT",
                is_stuck_or_deadlocked=False,
                is_dangerous=True,
                suggested_action=VLMActionType.PAUSE,
                target_coordinates=cancel_coords,
                target_element_description="Cancel Button",
                reasoning="Prompt asking to spend Gems detected. Overriding all clicks and pausing farming to prevent accidental loss.",
                source_model="local_florence_fallback"
            )

        if is_reload:
            reload_coords = [0.500, 0.595]
            for w_item in words:
                if "reload" in w_item["text"].lower():
                    h, w = frame_bgr.shape[:2]
                    cx, cy = w_item["center"]
                    reload_coords = [float(cx / float(w)), float(cy / float(h))]
                    break

            return VLMReasoningResult(
                scene_summary=f"Client out of sync / Reload Game dialog: {caption}",
                screen_classification="RELOAD_SYNC",
                is_stuck_or_deadlocked=True,
                is_dangerous=False,
                suggested_action=VLMActionType.DISMISS_POPUP,
                target_coordinates=reload_coords,
                target_element_description="Reload Game Button",
                reasoning="Game reported connection sync loss. Clicking Reload Game button to restart session.",
                source_model="local_florence_fallback"
            )

        if is_maintenance:
            return VLMReasoningResult(
                scene_summary=f"Supercell game maintenance break in progress: {caption}",
                screen_classification="MAINTENANCE",
                is_stuck_or_deadlocked=True,
                is_dangerous=False,
                suggested_action=VLMActionType.WAIT,
                reasoning="Game is under scheduled maintenance. Recommending wait cycle until maintenance ends.",
                source_model="local_florence_fallback"
            )

        if close_pt is not None:
            return VLMReasoningResult(
                scene_summary=f"Generic modal dialog or promotional banner with Close 'X': {caption}",
                screen_classification="PROMO_MODAL",
                is_stuck_or_deadlocked=False,
                is_dangerous=False,
                suggested_action=VLMActionType.DISMISS_POPUP,
                target_coordinates=[float(close_pt[0]), float(close_pt[1])],
                target_element_description="Modal Red Close 'X'",
                reasoning="Detected open modal overlay with red close button in top-right quadrant. Dismissing modal.",
                source_model="local_florence_fallback"
            )

        # Default fallback analysis
        return VLMReasoningResult(
            scene_summary=f"Unclassified game screen: {caption}",
            screen_classification="UNKNOWN",
            is_stuck_or_deadlocked=False,
            is_dangerous=False,
            suggested_action=VLMActionType.WAIT,
            reasoning=f"Screen not recognized by standard patterns. Full OCR text: '{text_content[:80]}...'. Waiting for transition.",
            source_model="local_florence_fallback"
        )


def get_shared_vlm_engine() -> MultimodalVLMEngine:
    """Returns the shared global MultimodalVLMEngine singleton."""
    global _SHARED_VLM_ENGINE
    if _SHARED_VLM_ENGINE is None:
        _SHARED_VLM_ENGINE = MultimodalVLMEngine()
    return _SHARED_VLM_ENGINE
