"""
Battle Status Detector.
Extracts battle timer, total damage percentage, star count, and end/surrender buttons.
Calibrated to exact Clash of Clans PC HUD layout.
"""

from __future__ import annotations
import logging
from typing import Optional, Callable
import time
import cv2
import numpy as np
from src.state.game_state import BattleInfo, DetectionResult, BoundingBox
from src.vision.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class BattleDetector:
    """Monitors live battle progress (timer, destruction %, end buttons)."""

    def __init__(self, ocr_engine: Optional[OCREngine] = None):
        self.ocr = ocr_engine or OCREngine()

    def detect_battle_status(self, frame_bgr: np.ndarray, frame_provider: Optional[Callable[[], np.ndarray]] = None) -> DetectionResult[BattleInfo]:
        h, w, _ = frame_bgr.shape
        if h == 0 or w == 0:
            return DetectionResult(value=BattleInfo(), confidence=0.0, errors=["Empty frame"])

        if frame_provider is None:
            num_samples = 1
        else:
            num_samples = 5
            
        observations = []
        import time
        for _ in range(num_samples):
            frame = frame_provider() if frame_provider else frame_bgr
            if frame is None or frame.size == 0:
                continue
                
            fh, fw, _ = frame.shape
            # Damage % area: bottom-right on castle wall
            damage_crop = frame[int(fh * 0.700):int(fh * 0.830), int(fw * 0.820):int(fw * 0.995)]
            obs_damage = self.ocr.read_percentage(damage_crop)

            # Timer area: top-center
            timer_crop = frame[int(fh * 0.010):int(fh * 0.100), int(fw * 0.420):int(fw * 0.580)]
            obs_timer = self.ocr.read_timer(timer_crop)

            # Detect End Battle / Surrender button in bottom-left
            btn_crop = frame[int(fh * 0.700):int(fh * 0.830), int(fw * 0.010):int(fw * 0.150)]
            obs_btn = self.ocr.read_text(btn_crop)
            
            observations.append({
                "damage": obs_damage,
                "timer": obs_timer,
                "btn": obs_btn
            })
            
            if frame_provider and _ < num_samples - 1:
                time.sleep(0.05)

        if not observations:
             return DetectionResult(value=BattleInfo(), confidence=0.0, errors=["No observations"])

        if num_samples == 1:
            damage_val, damage_conf = observations[0]["damage"]
            timer_val, timer_conf = observations[0]["timer"]
            btn_text, btn_conf = observations[0]["btn"]
        else:
            from src.vision.temporal_aggregator import TemporalAggregator
            def make_fetcher(key):
                it = iter([obs[key] for obs in observations])
                return lambda: next(it)

            damage_val, damage_conf = TemporalAggregator.aggregate(make_fetcher("damage"), num_samples=len(observations), delay_between_samples=0)
            timer_val, timer_conf = TemporalAggregator.aggregate(make_fetcher("timer"), num_samples=len(observations), delay_between_samples=0)
            btn_text, btn_conf = TemporalAggregator.aggregate(make_fetcher("btn"), num_samples=len(observations), delay_between_samples=0)

        btn_clean = (btn_text or "").lower()


        can_end = "end" in btn_clean or "battle" in btn_clean
        can_surrender = "surrender" in btn_clean

        is_active = (timer_val is not None and timer_val > 0) or can_end or can_surrender or (damage_val is not None and damage_val > 0)

        confs = [c for c in [damage_conf, timer_conf, btn_conf] if c > 0]
        avg_conf = float(np.mean(confs)) if confs else 0.85

        info = BattleInfo(
            is_active=is_active,
            damage_percent=damage_val if damage_val is not None else 0.0,
            time_remaining_seconds=timer_val if timer_val is not None else 180,
            stars=1 if (damage_val is not None and damage_val >= 50.0) else 0,
            can_end_battle=can_end or (damage_val is not None and damage_val >= 50.0),
            can_surrender=can_surrender or (damage_val is not None and damage_val < 50.0),
            confidence=avg_conf
        )

        return DetectionResult(
            value=info,
            confidence=avg_conf,
            bbox=BoundingBox(x=int(w * 0.840), y=int(h * 0.740), width=int(w * 0.155), height=int(h * 0.090))
        )
