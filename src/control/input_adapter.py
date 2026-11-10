"""
Input Adapter for Live Execution.
Provides direct Win32 API hardware mouse events (SetCursorPos + mouse_event + PostMessage)
and hardware keyboard events (pyautogui + WM_KEYDOWN) with robust window handle resolution.
"""

from __future__ import annotations
import time
import random
import ctypes
from ctypes import wintypes
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any
import pyautogui
from src.calibration.viewport import ViewportCalibrator
from src.utils.audit_logger import audit_logger

logger = logging.getLogger(__name__)

# Configure PyAutoGUI safety features
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101


class BaseInputAdapter(ABC):
    """Abstract base for input execution."""

    @abstractmethod
    def click_normalized(self, norm_x: float, norm_y: float, delay_after: float = 0.1) -> None:
        pass

    @abstractmethod
    def send_key_press(self, key_char: str, delay_after: float = 0.05) -> None:
        pass

    @abstractmethod
    def tap_sequence(self, points: list[Tuple[float, float]], delay_between: float = 0.05) -> None:
        pass


class DryRunExecutor(BaseInputAdapter):
    """Mock input adapter for headless testing without mouse interaction."""

    def __init__(self, calibrator=None):
        self.calibrator = calibrator
        self.clicks = []
        self.action_history = []
        self.keys = []

    def click_normalized(self, norm_x: float, norm_y: float, delay_after: float = 0.1, reason: str = "") -> None:
        self.clicks.append((norm_x, norm_y))
        self.action_history.append({"action": "CLICK", "norm_x": norm_x, "norm_y": norm_y, "reason": reason})
        px, py = (int(norm_x * 1920), int(norm_y * 1080))
        if self.calibrator and hasattr(self.calibrator, "normalized_to_pixel"):
            px, py = self.calibrator.normalized_to_pixel(norm_x, norm_y)
        audit_logger.log_action("DRY_RUN_CLICK", px, py, norm_x, norm_y, reason=reason)

    def send_key_press(self, key_char: str, delay_after: float = 0.05) -> None:
        self.keys.append(key_char)
        self.action_history.append({"action": "KEY", "key": key_char})

    def tap_sequence(self, points: list[Tuple[float, float]], delay_between: float = 0.05) -> None:
        for pt_x, pt_y in points:
            self.click_normalized(pt_x, pt_y, delay_after=delay_between)


class RealInputExecutor(BaseInputAdapter):
    """Sends real hardware mouse clicks and keyboard events to Clash of Clans / LDPlayer / BlueStacks / GPG."""

    def __init__(self, calibrator: ViewportCalibrator, humanize: bool = True):
        self.calibrator = calibrator
        self.humanize = humanize

    def _get_hwnd(self) -> Optional[int]:
        if hasattr(self.calibrator, "geometry") and self.calibrator.geometry.hwnd:
            return self.calibrator.geometry.hwnd
        return getattr(self.calibrator, "hwnd", None)

    def click_normalized(self, norm_x: float, norm_y: float, delay_after: float = 0.1, reason: str = "") -> None:
        px, py = self.calibrator.normalized_to_pixel(norm_x, norm_y)

        if self.humanize:
            jitter_x = random.randint(-1, 1)
            jitter_y = random.randint(-1, 1)
            px = max(0, px + jitter_x)
            py = max(0, py + jitter_y)

        # Register cursor move in extensive audit log
        audit_logger.log_cursor_move(px, py, norm_x, norm_y, reason=reason)

        # 1. Hardware Cursor Move & Physical Mouse Event
        try:
            ctypes.windll.user32.SetCursorPos(int(px), int(py))
            time.sleep(0.015)
            audit_logger.log_mouse_event("LEFT_DOWN", px, py, norm_x, norm_y, details="mouse_event(MOUSEEVENTF_LEFTDOWN)")
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.035)
            audit_logger.log_mouse_event("LEFT_UP", px, py, norm_x, norm_y, details="mouse_event(MOUSEEVENTF_LEFTUP)")
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception as e:
            audit_logger.log_mouse_event("FALLBACK_CLICK", px, py, norm_x, norm_y, details=f"pyautogui fallback: {e}")
            pyautogui.click(int(px), int(py))

        # 2. Direct Window Message to Game HWND for background/emulator compatibility
        hwnd = self._get_hwnd()
        if hwnd:
            try:
                geom = getattr(self.calibrator, "geometry", None)
                client_w = geom.window_width if geom else 1920
                client_h = geom.window_height if geom else 1080
                cx = max(0, min(client_w, int(norm_x * client_w)))
                cy = max(0, min(client_h, int(norm_y * client_h)))
                lparam = (cy << 16) | (cx & 0xFFFF)
                audit_logger.log_window_message("WM_LBUTTONDOWN", hwnd, cx, cy, lparam)
                ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
                time.sleep(0.02)
                audit_logger.log_window_message("WM_LBUTTONUP", hwnd, cx, cy, lparam)
                ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
            except Exception as e:
                audit_logger.log_mouse_event("WIN32_POST_ERROR", px, py, norm_x, norm_y, details=f"PostMessage error: {e}")

        time.sleep(delay_after)

    def send_key_press(self, key_char: str, delay_after: float = 0.05) -> None:
        """Sends a hardware keypress for Google Play Games on PC."""
        if not key_char:
            return

        try:
            pyautogui.press(key_char.lower())
        except Exception:
            pass

        hwnd = self._get_hwnd()
        if hwnd:
            try:
                vk_code = ord(key_char.upper())
                ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, 0)
                time.sleep(0.02)
                ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP, vk_code, 0)
            except Exception:
                pass

        time.sleep(delay_after)

    def tap_sequence(self, points: list[Tuple[float, float]], delay_between: float = 0.05) -> None:
        for pt_x, pt_y in points:
            self.click_normalized(pt_x, pt_y, delay_after=delay_between)
