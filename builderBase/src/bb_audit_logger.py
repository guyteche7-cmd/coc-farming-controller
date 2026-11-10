"""
Builder Base Decision & Action Audit Logger.
Maintains a dedicated, high-detail human-readable log file (data/logs/builder_base_audit.log)
recording step-by-step UI detection, click coordinates (screen + normalized),
army deployment taps, combat timer ticks, exit decisions, visual anomaly snapshots, and errors.
"""

from __future__ import annotations
import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Any
import cv2
import numpy as np

# Root data logs path
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "logs"))
SNAPSHOT_DIR = os.path.join(LOG_DIR, "snapshots")
BB_AUDIT_LOG_FILE = os.path.join(LOG_DIR, "builder_base_audit.log")

logger = logging.getLogger("builderBase.audit")


class BBAuditLogger:
    """Singleton audit logger for Builder Base 2.0 autonomous combat."""

    _instance: Optional[BBAuditLogger] = None

    def __new__(cls) -> BBAuditLogger:
        if cls._instance is None:
            cls._instance = super(BBAuditLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self.file_path = BB_AUDIT_LOG_FILE
        self._write_header()

    def _write_header(self) -> None:
        with open(self.file_path, "a", encoding="utf-8") as f:
            sep = "=" * 85
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{sep}\n")
            f.write(f"=== BUILDER BASE 2.0 DECISION & ACTION AUDIT LOG — SESSION START [{now}] ===\n")
            f.write(f"{sep}\n\n")

    def _format_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _log_entry(self, category: str, message: str) -> None:
        ts = self._format_timestamp()
        line = f"[{ts}] [{category:<14}] {message}\n"
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logger.error(f"Failed writing to BB audit log: {e}")

    def log_session_event(self, event_name: str, session_id: str, details: str = "") -> None:
        """Logs lifecycle changes: Session Started, Stopped, Paused, Resumed, Completed."""
        msg = f"Session '{session_id}' -> {event_name.upper()}."
        if details:
            msg += f" ({details})"
        self._log_entry("SESSION", msg)
        logger.info(f"[BB AUDIT SESSION] {msg}")

    def log_detection(self, state_name: str, confidence: float, details: str = "", active_slots: Optional[List[int]] = None) -> None:
        """Logs UI state detection with confidence percentage and active slot breakdown."""
        acc_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        slots_str = f" | Active Troop Slots: {active_slots}" if active_slots else ""
        msg = f"UI State: '{state_name}' ({acc_pct}% confidence){slots_str}."
        if details:
            msg += f" [{details}]"
        self._log_entry("DETECTION", msg)
        logger.info(f"[BB AUDIT DETECTION] {msg}")

    def log_click(
        self,
        action_name: str,
        norm_x: float,
        norm_y: float,
        pixel_x: Optional[int] = None,
        pixel_y: Optional[int] = None,
        reason: str = ""
    ) -> None:
        """Logs physical mouse click with normalized and pixel coordinates."""
        px_str = f" -> Pixel ({pixel_x}, {pixel_y})" if pixel_x is not None and pixel_y is not None else ""
        msg = f"Clicked '{action_name}' at Norm ({norm_x:.3f}, {norm_y:.3f}){px_str}."
        if reason:
            msg += f" Reason: {reason}"
        self._log_entry("CLICK", msg)
        logger.info(f"[BB AUDIT CLICK] {msg}")

    def log_deployment(
        self,
        unit_type: str,
        slot_idx: int,
        tap_num: int,
        total_taps: int,
        norm_x: float,
        norm_y: float,
        pixel_x: Optional[int] = None,
        pixel_y: Optional[int] = None
    ) -> None:
        """Logs individual troop or hero deployment taps."""
        px_str = f" [Pixel: ({pixel_x}, {pixel_y})]" if pixel_x is not None else ""
        msg = f"Deploying {unit_type} (Slot #{slot_idx}) -> Tap {tap_num}/{total_taps} at Norm ({norm_x:.3f}, {norm_y:.3f}){px_str}."
        self._log_entry("DEPLOYMENT", msg)
        logger.info(f"[BB AUDIT DEPLOY] {msg}")

    def log_combat_status(self, elapsed_seconds: float, decision: str, reason: str = "") -> None:
        """Logs combat timer and exit evaluator decisions."""
        mins, secs = divmod(int(elapsed_seconds), 60)
        formatted = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        msg = f"Combat Elapsed: {formatted} -> Decision: {decision.upper()}."
        if reason:
            msg += f" ({reason})"
        self._log_entry("COMBAT_EVAL", msg)
        logger.info(f"[BB AUDIT COMBAT] {msg}")

    def log_attack_summary(self, attack_number: int, total_attacks: int, status: str = "COMPLETED") -> None:
        """Logs completion of an attack."""
        msg = f"Attack #{attack_number} of {total_attacks} {status.upper()}."
        self._log_entry("ATTACK_RESULT", msg)
        logger.info(f"[BB AUDIT ATTACK] {msg}")

    def log_focus_guard(self, is_focused: bool, window_title: str = "") -> None:
        """Logs window focus guard interventions."""
        status = "FOCUSED" if is_focused else "LOST FOCUS (Pausing inputs)"
        msg = f"Game Window '{window_title}' -> {status}."
        self._log_entry("FOCUS_GUARD", msg)
        logger.warning(f"[BB AUDIT FOCUS] {msg}")

    def log_anomaly_snapshot(self, frame: np.ndarray, reason: str = "unknown_state") -> Optional[str]:
        """Saves a downsampled visual snapshot to data/logs/snapshots/ for offline diagnosis."""
        if frame is None or frame.size == 0:
            return None
        try:
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"bb_snapshot_{ts}_{reason}.jpg"
            filepath = os.path.join(SNAPSHOT_DIR, filename)
            cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            msg = f"Visual anomaly snapshot captured: {filename} (Reason: {reason})"
            self._log_entry("SNAPSHOT", msg)
            logger.info(f"[BB AUDIT SNAPSHOT] {msg}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save visual snapshot: {e}")
            return None

    def log_error(self, component: str, error_message: str, exc_str: Optional[str] = None) -> None:
        """Logs errors and exceptions in Builder Base routines."""
        msg = f"[{component}] ERROR: {error_message}"
        if exc_str:
            msg += f"\nStack Trace:\n{exc_str}"
        self._log_entry("ERROR", msg)
        logger.error(f"[BB AUDIT ERROR] {msg}")


# Global singleton instance
bb_audit = BBAuditLogger()
