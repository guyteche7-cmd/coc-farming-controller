"""
Storage Inspector & Capacity Calibrator.
Detects player profile name, dynamic storage maximum limits via HUD tooltip OCR,
and monitors current Gold and Elixir storage fullness to enforce internal attack limits.
"""

from __future__ import annotations
import logging
import re
from typing import Optional, Tuple, Dict
import cv2
import numpy as np

from src.vision.ocr_engine import OCREngine
from src.vision.glyph_reader import SupercellGlyphReader

logger = logging.getLogger(__name__)


class StorageInspector:
    """Extracts player identity, inspects storage tooltips, and reads current HUD resources."""

    def __init__(self, ocr_engine: Optional[OCREngine] = None, glyph_reader: Optional[SupercellGlyphReader] = None):
        self.ocr = ocr_engine or OCREngine()
        self.glyph_reader = glyph_reader or SupercellGlyphReader()

    def detect_player_name(self, frame_bgr: np.ndarray) -> str:
        """
        Extracts the player username from top-left HUD (beside level/town hall badge).
        Expected region: norm_x: [0.07, 0.25], norm_y: [0.05, 0.14].
        Uses PP-OCRv4 with backward-compatible line fallback.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return ""

        # High-accuracy PP-OCR player perception
        if hasattr(self.ocr, "read_player_info"):
            info = self.ocr.read_player_info(frame_bgr)
            if info and info.get("player_name"):
                name = info["player_name"]
                logger.info(f"[STORAGE INSPECTOR] Detected Player ID via PP-OCR: '{name}'")
                return name

        h, w, _ = frame_bgr.shape
        crop = frame_bgr[int(h * 0.05):int(h * 0.14), int(w * 0.07):int(w * 0.25)]
        
        # Preprocess: grayscale & resize for clean OCR
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
        lines = self.ocr.reader.readtext(resized) if hasattr(self.ocr, "reader") and self.ocr.reader else []
        if not lines:
            text, _ = self.ocr.read_text(resized)
            lines = [([], text, 0.5)] if text else []

        for _, raw_text, conf in lines:
            clean = raw_text.strip()
            # Ignore clan titles or generic badges if identifiable
            if clean and len(clean) >= 2 and not clean.lower().startswith("clan"):
                # Clean invalid symbols
                clean = re.sub(r"[^\w\s-]", "", clean).strip()
                if clean:
                    logger.info(f"[STORAGE INSPECTOR] Detected Player ID: '{clean}' (conf={conf:.2f})")
                    return clean

        return ""

    def read_max_capacity_tooltip(self, frame_bgr: np.ndarray, resource_type: str = "gold") -> int:
        """
        Reads 'Max: <number>' from the active storage tooltip.
        - For Gold: tooltip appears at norm_y: [0.07, 0.18], norm_x: [0.70, 0.98]
        - For Elixir: tooltip appears at norm_y: [0.14, 0.25], norm_x: [0.70, 0.98]
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return 0

        h, w, _ = frame_bgr.shape
        if resource_type.lower() == "elixir":
            crop = frame_bgr[int(h * 0.13):int(h * 0.26), int(w * 0.70):int(w * 0.98)]
        else:
            crop = frame_bgr[int(h * 0.06):int(h * 0.19), int(w * 0.70):int(w * 0.98)]

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_LINEAR)

        lines = self.ocr.reader.readtext(resized) if hasattr(self.ocr, "reader") and self.ocr.reader else []
        if not lines:
            text, _ = self.ocr.read_text(resized)
            lines = [([], text, 0.5)] if text else []

        for _, raw_text, conf in lines:
            txt = raw_text.lower()
            if "max" in txt or "mak" in txt or "mas" in txt:
                val = self._sanitize_max_capacity(raw_text)
                if val > 0:
                    logger.info(f"[STORAGE INSPECTOR] Parsed Max {resource_type.capitalize()}: {val:,} from '{raw_text}' (conf={conf:.2f})")
                    return val

        return 0

    def read_current_resources(self, frame_bgr: np.ndarray) -> Tuple[int, int, int]:
        """
        Reads current Gold, Elixir, and Dark Elixir from the top-right HUD.
        Returns: (current_gold, current_elixir, current_dark_elixir)
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return (0, 0, 0)

        h, w, _ = frame_bgr.shape

        # Gold HUD number: norm_x: [0.82, 0.96], norm_y: [0.025, 0.075]
        crop_g = frame_bgr[int(h * 0.025):int(h * 0.075), int(w * 0.82):int(w * 0.96)]
        # Elixir HUD number: norm_x: [0.82, 0.96], norm_y: [0.095, 0.145]
        crop_e = frame_bgr[int(h * 0.095):int(h * 0.145), int(w * 0.82):int(w * 0.96)]
        # Dark Elixir HUD number: norm_x: [0.82, 0.96], norm_y: [0.165, 0.215]
        crop_de = frame_bgr[int(h * 0.165):int(h * 0.215), int(w * 0.82):int(w * 0.96)]

        gold, _ = self.glyph_reader.read_integer(crop_g)
        if gold == 0:
            gold = self._ocr_resource_number(crop_g)

        elixir, _ = self.glyph_reader.read_integer(crop_e)
        if elixir == 0:
            elixir = self._ocr_resource_number(crop_e)

        dark_elixir, _ = self.glyph_reader.read_integer(crop_de)
        if dark_elixir == 0:
            dark_elixir = self._ocr_resource_number(crop_de)

        return (gold, elixir, dark_elixir)

    def _ocr_resource_number(self, crop_bgr: np.ndarray) -> int:
        if crop_bgr is None or crop_bgr.size == 0:
            return 0
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        lines = self.ocr.reader.readtext(resized) if hasattr(self.ocr, "reader") and self.ocr.reader else []
        if not lines:
            text, _ = self.ocr.read_text(resized)
            lines = [([], text, 0.5)] if text else []

        for _, raw_text, _ in lines:
            clean = re.sub(r"[^\d]", "", raw_text)
            if clean:
                val = int(clean)
                if 100 <= val <= 50_000_000:
                    return val
        return 0

    def _sanitize_max_capacity(self, raw_text: str) -> int:
        """Sanitizes OCR string from tooltip into an exact integer capacity."""
        m = re.search(r"(?:max|mak|mas)[\s:]*(.*)", raw_text, re.IGNORECASE)
        if not m:
            return 0

        rest = m.group(1).strip()
        # Extract all digit clusters in remainder (e.g. '31', '000', '000' even if separated by 't', ',', or space)
        digit_groups = re.findall(r"\d+", rest)
        if not digit_groups:
            return 0

        digits = "".join(digit_groups)
        val = int(digits)

        # Handle OCR artifact where a thousands separator was read as an extra digit (e.g. 9 digits)
        if val > 40_000_000 and len(digits) == 9:
            val = int(digits[:2]) * 1_000_000 + int(digits[2:5]) * 1_000

        # Handle OCR artifact where a zero was omitted in a triplet (e.g. 31,00 000 -> 31,000,000)
        if len(digits) == 7 and val >= 1_000_000 and digits[2:] == "00000":
            val = val * 10

        # Validate reasonable CoC storage capacity range: 10,000 to 40,000,000
        if 10_000 <= val <= 40_000_000:
            return val

        return 0
