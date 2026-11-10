"""
Decision Audit Logger.
Maintains a separate, high-detail human-readable log file (data/logs/decision_audit.log)
recording step-by-step detection accuracy, click coordinates (screen + normalized),
popup transitions, loot evaluations, unit deployments, hero ability triggers, and visual snapshots.
"""

from __future__ import annotations
import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple, Any
import cv2
import numpy as np

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "logs")
SNAPSHOT_DIR = os.path.join(LOG_DIR, "snapshots")
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "decision_audit.log")


class DecisionAuditLogger:
    """Singleton audit logger for step-by-step game decision feedback."""

    _instance: Optional[DecisionAuditLogger] = None

    def __new__(cls) -> DecisionAuditLogger:
        if cls._instance is None:
            cls._instance = super(DecisionAuditLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self.file_path = AUDIT_LOG_FILE
        self._write_header()

    def _write_header(self) -> None:
        with open(self.file_path, "a", encoding="utf-8") as f:
            sep = "=" * 80
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{sep}\n")
            f.write(f"=== CLASH OF CLANS DECISION & FEEDBACK AUDIT LOG — SESSION START [{now}] ===\n")
            f.write(f"{sep}\n\n")

    def _format_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _log_entry(self, category: str, message: str) -> None:
        ts = self._format_timestamp()
        line = f"[{ts}] [{category:<12}] {message}\n"
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def log_detection(self, state_name: str, confidence: float, details: str = "") -> None:
        """Logs UI state or button detection with percentage accuracy."""
        acc_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        msg = f"Detected '{state_name}' with {acc_pct}% accuracy."
        if details:
            msg += f" Details: {details}"
        self._log_entry("DETECTION", msg)

    def log_action(
        self,
        action_name: str,
        pixel_x: int,
        pixel_y: int,
        norm_x: float,
        norm_y: float,
        reason: str = ""
    ) -> None:
        """Logs physical mouse click with screen pixel and normalized coordinates."""
        msg = f"Clicked '{action_name}' at Screen ({pixel_x}, {pixel_y}) [Norm: ({norm_x:.3f}, {norm_y:.3f})]."
        if reason:
            msg += f" (Reason: {reason})"
        self._log_entry("ACTION", msg)

    def log_cursor_move(
        self,
        pixel_x: int,
        pixel_y: int,
        norm_x: float,
        norm_y: float,
        reason: str = ""
    ) -> None:
        """Logs physical mouse cursor movement."""
        msg = f"Moved cursor to Screen ({pixel_x}, {pixel_y}) [Norm: ({norm_x:.3f}, {norm_y:.3f})]."
        if reason:
            msg += f" (Reason: {reason})"
        self._log_entry("CURSOR_MOVE", msg)

    def log_mouse_event(
        self,
        event_name: str,
        pixel_x: int,
        pixel_y: int,
        norm_x: float,
        norm_y: float,
        details: str = ""
    ) -> None:
        """Logs granular hardware mouse events (LEFT_DOWN, LEFT_UP, TAP)."""
        msg = f"{event_name} at Screen ({pixel_x}, {pixel_y}) [Norm: ({norm_x:.3f}, {norm_y:.3f})]."
        if details:
            msg += f" {details}"
        self._log_entry("MOUSE_EVENT", msg)

    def log_window_message(
        self,
        msg_name: str,
        hwnd: int,
        client_x: int,
        client_y: int,
        lparam: int
    ) -> None:
        """Logs direct Win32 message sent to emulator HWND for background/emulator compatibility."""
        msg = f"PostMessageW {msg_name} to HWND 0x{hwnd:08X} at client coords ({client_x}, {client_y}) [lParam=0x{lparam:08X}]."
        self._log_entry("WIN32_MSG", msg)

    def log_state_tick(
        self,
        tick: int,
        state_name: str,
        confidence: float,
        fg_info: str = "",
        details: str = ""
    ) -> None:
        """Logs live state evaluation tick, active foreground window, and transition status."""
        acc_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        msg = f"Tick #{tick} | State: {state_name} ({acc_pct}%) | Active: {fg_info}"
        if details:
            msg += f" | {details}"
        self._log_entry("STATE_TICK", msg)

    def log_step_blocked(self, reason: str) -> None:
        """Logs why an execution tick was skipped or prevented from clicking."""
        self._log_entry("STEP_BLOCKED", f"Action execution skipped: {reason}")

    def log_session_event(self, event_name: str, session_id: str, details: str = "") -> None:
        """Logs session lifecycle events (start, pause, resume, stop)."""
        msg = f"Session [{session_id}] -> {event_name}"
        if details:
            msg += f" ({details})"
        self._log_entry("SESSION", msg)

    def log_loot_scan(
        self,
        base_num: int,
        gold: int,
        elixir: int,
        dark_elixir: int,
        confidence: float,
        accepted: bool,
        reason: str = ""
    ) -> None:
        """Logs candidate base loot scan and acceptance/skip decision."""
        acc_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
        status_str = "ACCEPTED (Deploying Army)" if accepted else "SKIPPED (Next Base)"
        msg = (
            f"Candidate Base #{base_num} Scanned ({acc_pct}% OCR confidence) -> "
            f"Gold: {gold:,} | Elixir: {elixir:,} | Dark Elixir: {dark_elixir:,} -> "
            f"Decision: {status_str}. {reason}"
        )
        self._log_entry("LOOT_SCAN", msg)

    def log_deployment_step(
        self,
        slot_idx: Optional[int],
        slot_name: str,
        pixel_x: int,
        pixel_y: int,
        norm_x: float,
        norm_y: float,
        tap_count: int = 1,
        desc: str = ""
    ) -> None:
        """Logs troop/siege/spell deployment step with exact coordinates and tap counts."""
        slot_str = f"Slot {slot_idx} ({slot_name})" if slot_idx is not None else slot_name
        msg = (
            f"Deploying {slot_str} -> {tap_count} tap(s) at Screen ({pixel_x}, {pixel_y}) "
            f"[Norm: ({norm_x:.3f}, {norm_y:.3f})]. {desc}"
        )
        self._log_entry("DEPLOYMENT", msg)

    def log_hero_ability(
        self,
        slot_idx: int,
        hero_name: str,
        pixel_x: int,
        pixel_y: int,
        norm_x: float,
        norm_y: float
    ) -> None:
        """Logs hero ability activation."""
        msg = (
            f"Activated Hero Ability for Slot {slot_idx} ({hero_name}) by re-clicking ribbon at "
            f"Screen ({pixel_x}, {pixel_y}) [Norm: ({norm_x:.3f}, {norm_y:.3f})]."
        )
        self._log_entry("ABILITY", msg)

    def log_combat_status(
        self,
        damage_percent: float,
        stars: int,
        time_stagnant_sec: float,
        status: str = "Monitoring combat"
    ) -> None:
        """Logs combat progression, damage %, and destruction stagnation."""
        msg = (
            f"Combat Progress -> Damage: {damage_percent:.0f}% | Stars: {stars} | "
            f"Damage Stagnant: {time_stagnant_sec:.1f}s | Status: {status}"
        )
        self._log_entry("COMBAT", msg)

    def log_battle_exit(
        self,
        decision: str,
        final_damage: float,
        stars: int,
        button_clicked: str,
        pixel_x: int,
        pixel_y: int
    ) -> None:
        """Logs battle completion, surrender, or return home action."""
        msg = (
            f"Battle Complete -> Decision: {decision} with {final_damage:.0f}% damage ({stars} stars). "
            f"Clicked '{button_clicked}' at Screen ({pixel_x}, {pixel_y})."
        )
        self._log_entry("BATTLE_END", msg)

    def log_anomaly_snapshot(self, frame: np.ndarray, reason: str = "unknown_state") -> Optional[str]:
        """Saves visual debug snapshot on anomaly or unexpected state."""
        if frame is None or frame.size == 0:
            return None
        try:
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"hv_snapshot_{ts}_{reason}.jpg"
            filepath = os.path.join(SNAPSHOT_DIR, filename)
            cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            msg = f"Visual anomaly snapshot captured: {filename} (Reason: {reason})"
            self._log_entry("SNAPSHOT", msg)
            return filepath
        except Exception:
            return None


# Global singleton instance
audit_logger = DecisionAuditLogger()
