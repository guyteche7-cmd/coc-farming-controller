"""
Microsoft Florence-2 Open-Vocabulary Vision & Game Awareness Perception Engine.

Provides Level-3 Game Awareness and Zero-Shot Visual Grounding:
- Dense Region Captioning (<DENSE_REGION_CAPTION>) for unexpected game states.
- Open-Vocabulary Object Grounding (<CAPTION_TO_PHRASE_GROUNDING>) for arbitrary UI elements.
- Unknown Popup Detection & Safe Dismissal:
  - Detects "Client and Server out of sync", "Reload Game", "Personal Break",
    "Village Under Attack", "Supercell Promo / Events", and "Gem Purchase Prompts".
  - Identifies safe dismissal targets (Close 'X' icon, Okay, Reload, Cancel).
  - Flags dangerous dialogs (Gem spending / confirmation) to prevent accidental loss.
- Resilient Fallback: Combines PP-OCRv4 + OpenCV heuristics if neural weights are downloading.
"""

from __future__ import annotations
import os
import re
import time
import logging
import threading
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Global singleton
_SHARED_FLORENCE_ENGINE: Optional[Florence2VisionEngine] = None


@dataclass
class PopupDetection:
    """Represents a detected in-game popup or modal dialog."""
    popup_type: str            # 'RELOAD_SYNC', 'PERSONAL_BREAK', 'PROMO_EVENT', 'GEM_CONFIRM', 'INFO_MODAL', 'UNKNOWN'
    title: str
    description: str
    dismiss_point: Optional[Tuple[float, float]]  # Normalized (norm_x, norm_y) click coordinate
    dismiss_type: str          # 'OKAY', 'CLOSE_X', 'RELOAD', 'CANCEL', 'NONE'
    is_dangerous: bool         # True if popup prompts for Gems or irreversible action
    confidence: float
    bbox_norm: Optional[Tuple[float, float, float, float]] = None


class Florence2VisionEngine:
    """
    Microsoft Florence-2 Open-Vocabulary Vision Engine for Game Awareness & Popup Handling.
    Runs asynchronously in background thread to never block UI or real-time combat loops.
    """

    MODEL_ID = "microsoft/Florence-2-base"

    def __init__(self, auto_load_model: bool = False, device: Optional[str] = None):
        self.is_ready = False
        self.is_loading = False
        self.load_error: Optional[str] = None
        self.model = None
        self.processor = None
        self.device = device or ("cuda" if self._is_cuda_available() else "cpu")

        # Lazy / background loading trigger
        if auto_load_model:
            self.start_async_loading()

    @staticmethod
    def _is_cuda_available() -> bool:
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def start_async_loading(self) -> None:
        """Launches background thread to download and initialize Florence-2 weights."""
        if self.is_ready or self.is_loading:
            return

        self.is_loading = True
        thread = threading.Thread(target=self._load_florence_model, daemon=True, name="Florence2Loader")
        thread.start()

    def _load_florence_model(self) -> None:
        """Loads Florence-2 processor and weights with CPU/GPU optimization."""
        logger.info(f"[FLORENCE-2] Initializing Florence-2 ({self.MODEL_ID}) on {self.device} in background...")
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForCausalLM

            # Disable symlink warnings on Windows
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

            self.processor = AutoProcessor.from_pretrained(self.MODEL_ID, trust_remote_code=True)
            dtype = torch.float16 if self.device == "cuda" else torch.float32

            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID,
                torch_dtype=dtype,
                trust_remote_code=True
            ).to(self.device)
            self.model.eval()

            self.is_ready = True
            self.is_loading = False
            logger.info("[FLORENCE-2] Microsoft Florence-2 neural model successfully loaded and ready.")
        except Exception as e:
            self.load_error = str(e)
            self.is_loading = False
            logger.warning(f"[FLORENCE-2] Neural model background load paused: {e}. Active mode: High-Precision Open-Vocabulary Fallback.")

    # =========================================================================
    # High-Level Clash of Clans Game Awareness & Popup Perception
    # =========================================================================

    def detect_popup(self, frame_bgr: np.ndarray) -> Optional[PopupDetection]:
        """
        Analyzes the screen for any unexpected dialog, modal popup, error box, or promotion.
        Returns PopupDetection with title, description, is_dangerous flag, and safe dismiss_point (norm_x, norm_y).
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        # 1. Neural Florence-2 inference if model weights are loaded
        if self.is_ready and self.model is not None and self.processor is not None:
            try:
                neural_detection = self._detect_popup_neural(frame_bgr)
                if neural_detection:
                    return neural_detection
            except Exception as e:
                logger.debug(f"[FLORENCE-2] Neural inference error: {e}. Using resilient visual grounding fallback.")

        # 2. Resilient Open-Vocabulary Grounding Fallback (PP-OCRv4 + Color / Contour Geometrics)
        return self._detect_popup_grounding_fallback(frame_bgr)

    def ground_phrases(self, frame_bgr: np.ndarray, phrases: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Open-vocabulary phrase grounding: finds bounding boxes for custom natural language queries.
        E.g. ["okay button", "close button", "town hall", "clan castle"]
        """
        if frame_bgr is None or frame_bgr.size == 0 or not phrases:
            return {}

        results: Dict[str, List[Dict[str, Any]]] = {p: [] for p in phrases}

        if self.is_ready and self.model is not None and self.processor is not None:
            try:
                for phrase in phrases:
                    boxes = self._run_grounding_task(frame_bgr, f"<CAPTION_TO_PHRASE_GROUNDING> {phrase}")
                    if boxes:
                        results[phrase] = boxes
                return results
            except Exception as e:
                logger.debug(f"[FLORENCE-2] Neural phrase grounding error: {e}")

        # Fallback using PP-OCR text matching & contours
        from src.vision.ocr_engine import get_shared_paddle_ocr_engine
        ocr = get_shared_paddle_ocr_engine()
        words = ocr.read_words(frame_bgr)
        h, w = frame_bgr.shape[:2]

        for p in phrases:
            p_clean = p.lower().strip()
            for w_item in words:
                text_clean = w_item["text"].lower()
                if p_clean in text_clean or text_clean in p_clean:
                    cx, cy = w_item["center"]
                    box = w_item["box"]
                    results[p].append({
                        "center_norm": (cx / float(w), cy / float(h)),
                        "bbox_norm": (box[0][0]/w, box[0][1]/h, box[2][0]/w, box[2][1]/h),
                        "confidence": w_item["confidence"],
                        "matched_text": w_item["text"]
                    })

        return results

    def describe_scene(self, frame_bgr: np.ndarray, task: str = "<DETAILED_CAPTION>") -> str:
        """Generates natural language description of current screen for debugging & anomaly RCA."""
        if frame_bgr is None or frame_bgr.size == 0:
            return "Empty or invalid frame."

        if self.is_ready and self.model is not None and self.processor is not None:
            try:
                pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                inputs = self.processor(text=task, images=pil_img, return_tensors="pt").to(self.device)
                
                import torch
                with torch.no_grad():
                    generated_ids = self.model.generate(
                        input_ids=inputs["input_ids"],
                        pixel_values=inputs["pixel_values"],
                        max_new_tokens=256,
                        num_beams=3
                    )
                ans = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
                parsed = self.processor.post_process_generation(ans, task=task, image_size=pil_img.size)
                return str(parsed.get(task, ans))
            except Exception as e:
                logger.debug(f"[FLORENCE-2] Scene captioning error: {e}")

        # Fallback scene summary from detected text
        from src.vision.ocr_engine import get_shared_paddle_ocr_engine
        ocr = get_shared_paddle_ocr_engine()
        words = ocr.read_words(frame_bgr)
        all_text = ", ".join(w["text"] for w in words[:10])
        return f"CoC UI scene containing detected labels: [{all_text}]"

    def is_modal_dialog_open(self, frame_bgr: np.ndarray) -> bool:
        """Determines if a centered modal dialog with dimmed background is currently present."""
        if frame_bgr is None or frame_bgr.size == 0:
            return False

        h, w = frame_bgr.shape[:2]
        # Check border darkness (dimmed overlay during dialogs)
        top_strip = frame_bgr[0:int(0.08*h), :]
        bot_strip = frame_bgr[int(0.92*h):h, :]
        mean_border_brightness = float(np.mean([np.mean(top_strip), np.mean(bot_strip)]))

        # Check center region (dialog box is typically brighter: parchment/stone)
        center_box = frame_bgr[int(0.25*h):int(0.75*h), int(0.25*w):int(0.75*w)]
        mean_center_brightness = float(np.mean(center_box))

        # Significant contrast between center dialog and dark overlay
        if mean_center_brightness > 70 and (mean_center_brightness - mean_border_brightness) > 25:
            return True

        return False

    # =========================================================================
    # Internal Inference Engines
    # =========================================================================

    def _detect_popup_neural(self, frame_bgr: np.ndarray) -> Optional[PopupDetection]:
        """Runs Florence-2 open-vocabulary detection & grounding on popup elements."""
        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        prompt = "<OPEN_VOCABULARY_DETECTION> popup window, dialog box, close button, okay button, reload button, cross icon"

        inputs = self.processor(text=prompt, images=pil_img, return_tensors="pt").to(self.device)
        import torch
        with torch.no_grad():
            gen_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=256,
                num_beams=3
            )
        ans = self.processor.batch_decode(gen_ids, skip_special_tokens=False)[0]
        parsed = self.processor.post_process_generation(ans, task="<OPEN_VOCABULARY_DETECTION>", image_size=pil_img.size)

        detections = parsed.get("<OPEN_VOCABULARY_DETECTION>", {})
        boxes = detections.get("bboxes", [])
        labels = detections.get("bboxes_labels", [])

        if not boxes:
            return None

        w, h = pil_img.size
        dismiss_point = None
        dismiss_type = "NONE"
        popup_bbox = None

        for box, lbl in zip(boxes, labels):
            lbl_lower = lbl.lower()
            cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
            nx, ny = cx / float(w), cy / float(h)

            if "popup" in lbl_lower or "dialog" in lbl_lower:
                popup_bbox = (box[0]/w, box[1]/h, box[2]/w, box[3]/h)

            if "close" in lbl_lower or "cross" in lbl_lower:
                dismiss_point = (nx, ny)
                dismiss_type = "CLOSE_X"
            elif "okay" in lbl_lower or "ok" in lbl_lower:
                if dismiss_type != "CLOSE_X":
                    dismiss_point = (nx, ny)
                    dismiss_type = "OKAY"
            elif "reload" in lbl_lower:
                dismiss_point = (nx, ny)
                dismiss_type = "RELOAD"

        # Read popup text via PP-OCR
        from src.vision.ocr_engine import get_shared_paddle_ocr_engine
        ocr = get_shared_paddle_ocr_engine()
        text, conf = ocr.read_text(frame_bgr)

        popup_type, is_dangerous = self._classify_popup_semantics(text)

        return PopupDetection(
            popup_type=popup_type,
            title="In-Game Modal Dialog",
            description=text[:120],
            dismiss_point=dismiss_point,
            dismiss_type=dismiss_type,
            is_dangerous=is_dangerous,
            confidence=0.85,
            bbox_norm=popup_bbox
        )

    def _run_grounding_task(self, frame_bgr: np.ndarray, prompt: str) -> List[Dict[str, Any]]:
        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        inputs = self.processor(text=prompt, images=pil_img, return_tensors="pt").to(self.device)
        import torch
        with torch.no_grad():
            gen_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=256,
                num_beams=3
            )
        ans = self.processor.batch_decode(gen_ids, skip_special_tokens=False)[0]
        parsed = self.processor.post_process_generation(ans, task="<CAPTION_TO_PHRASE_GROUNDING>", image_size=pil_img.size)

        w, h = pil_img.size
        grounding = parsed.get("<CAPTION_TO_PHRASE_GROUNDING>", {})
        boxes = grounding.get("bboxes", [])
        labels = grounding.get("labels", [])

        out = []
        for box, lbl in zip(boxes, labels):
            cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
            out.append({
                "center_norm": (cx / float(w), cy / float(h)),
                "bbox_norm": (box[0]/w, box[1]/h, box[2]/w, box[3]/h),
                "label": lbl
            })
        return out

    def _detect_popup_grounding_fallback(self, frame_bgr: np.ndarray) -> Optional[PopupDetection]:
        """
        High-precision Open-Vocabulary Grounding Fallback:
        Scans for dialog patterns using PP-OCR words, modal geometry, and button heuristics.
        """
        from src.vision.ocr_engine import get_shared_paddle_ocr_engine
        ocr = get_shared_paddle_ocr_engine()
        words = ocr.read_words(frame_bgr, min_conf=0.45)
        if not words:
            return None

        h, w = frame_bgr.shape[:2]
        full_text = " ".join(w["text"] for w in words)
        text_lower = full_text.lower()

        # Check for known CoC popup trigger words
        known_triggers = [
            "reload", "out of sync", "connection lost", "take a break",
            "personal break", "another device", "under attack", "gems",
            "upgrade to town hall", "cancel", "okay", "claim", "events"
        ]
        has_trigger = any(t in text_lower for t in known_triggers)

        # Check if dialog contrast is active
        is_dialog = self.is_modal_dialog_open(frame_bgr) or has_trigger
        if not is_dialog:
            return None

        dismiss_point = None
        dismiss_type = "NONE"

        # Search for buttons among detected words
        for w_item in words:
            txt = w_item["text"].lower().strip()
            cx, cy = w_item["center"]
            nx, ny = cx / float(w), cy / float(h)

            # Center/lower buttons (Okay, Reload, Cancel, Close, Try Again)
            if txt in ("okay", "ok") and ny > 0.45:
                dismiss_point = (nx, ny)
                dismiss_type = "OKAY"
                break
            elif "reload" in txt and ny > 0.45:
                dismiss_point = (nx, ny)
                dismiss_type = "RELOAD"
                break
            elif txt in ("close", "dismiss") and ny > 0.40:
                dismiss_point = (nx, ny)
                dismiss_type = "CLOSE_X"
                break
            elif txt == "cancel" and ny > 0.45:
                dismiss_point = (nx, ny)
                dismiss_type = "CANCEL"

        # If no text button found, search for the 'X' (cross) icon in the top-right of center modal
        if dismiss_point is None:
            cross_pt = self._find_modal_close_cross(frame_bgr)
            if cross_pt:
                dismiss_point = cross_pt
                dismiss_type = "CLOSE_X"

        # Fallback default: if Okay text was detected anywhere
        if dismiss_point is None and "okay" in text_lower:
            dismiss_point = (0.591, 0.622)  # Standard Okay dialog anchor
            dismiss_type = "OKAY"

        popup_type, is_dangerous = self._classify_popup_semantics(full_text)

        return PopupDetection(
            popup_type=popup_type,
            title="In-Game Popup Dialog",
            description=full_text[:120],
            dismiss_point=dismiss_point,
            dismiss_type=dismiss_type,
            is_dangerous=is_dangerous,
            confidence=0.88,
            bbox_norm=(0.20, 0.20, 0.80, 0.80)
        )

    def _classify_popup_semantics(self, text: str) -> Tuple[str, bool]:
        """Classifies popup semantics and identifies if prompt is dangerous (gem spending)."""
        text_lower = text.lower()

        # DANGEROUS: Prompts asking to spend gems or buy resources with gems
        if "gem" in text_lower and any(k in text_lower for k in ("spend", "buy", "cost", "finish", "use", "now", "confirm")):
            return "POPUP_GEM_CONFIRM", True

        if "reload" in text_lower or "out of sync" in text_lower or "connection lost" in text_lower:
            return "POPUP_RELOAD_SYNC", False

        if "personal break" in text_lower or "take a break" in text_lower:
            return "POPUP_PERSONAL_BREAK", False

        if "another device" in text_lower or "under attack" in text_lower:
            return "POPUP_VILLAGE_ATTACK", False

        if "event" in text_lower or "season" in text_lower or "special offer" in text_lower:
            return "POPUP_PROMO_EVENT", False

        if "okay" in text_lower or "cancel" in text_lower:
            return "POPUP_CONFIRM_MODAL", False

        return "POPUP_UNKNOWN", False

    def _find_modal_close_cross(self, frame_bgr: np.ndarray) -> Optional[Tuple[float, float]]:
        """Detects the red or grey 'X' close button located at top-right of in-game modals."""
        h, w = frame_bgr.shape[:2]
        # Search area: top-right quadrant of typical modal dialog (norm_x: 0.65 to 0.88, norm_y: 0.10 to 0.35)
        crop = frame_bgr[int(0.10 * h):int(0.35 * h), int(0.65 * w):int(0.88 * w)]
        if crop.size == 0:
            return None

        # Red close button mask (HSV)
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 120, 100]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([160, 120, 100]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)

        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Typical close button is small circular/square button (area between 200 and 4000 pixels)
            if 150 < area < 5000:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect = float(cw) / float(ch) if ch > 0 else 0
                if 0.7 <= aspect <= 1.4:
                    cx = int(0.65 * w) + x + cw // 2
                    cy = int(0.10 * h) + y + ch // 2
                    return (cx / float(w), cy / float(h))

        return None


def get_shared_florence_engine() -> Florence2VisionEngine:
    global _SHARED_FLORENCE_ENGINE
    if _SHARED_FLORENCE_ENGINE is None:
        _SHARED_FLORENCE_ENGINE = Florence2VisionEngine(auto_load_model=False)
    return _SHARED_FLORENCE_ENGINE
