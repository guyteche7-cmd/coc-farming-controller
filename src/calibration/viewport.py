"""
Viewport Calibration & Window Focus Guard System.
Locates the Clash of Clans / Google Play Games window on Windows PC, calculates
geometry transforms using Client Area (excluding title bars), provides window focusing,
and provides an active Foreground Window Safety Guard.
"""

from __future__ import annotations
import logging
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional, Dict, Any, List
from pydantic import BaseModel, Field
import pygetwindow as gw

logger = logging.getLogger(__name__)

# Ensure High DPI awareness so mouse coordinates match screen pixels accurately
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ViewportGeometry(BaseModel):
    screen_width: int = 1920
    screen_height: int = 1080
    window_x: int = 0
    window_y: int = 0
    window_width: int = 1920
    window_height: int = 1080
    scale_x: float = 1.0
    scale_y: float = 1.0
    is_fullscreen: bool = True
    confidence: float = 1.0
    hwnd: Optional[int] = None
    window_title: str = ""


class ViewportCalibrator:
    """Manages viewport detection, window focusing, and coordinate normalization."""

    def __init__(
        self,
        target_resolution: Tuple[int, int] = (1920, 1080),
        title_pattern: str = "Google Play Games|Clash of Clans|BlueStacks|LDPlayer|Nox|MuMu|HD-Player"
    ):
        self.target_resolution = target_resolution
        self.title_pattern = title_pattern
        self.geometry: ViewportGeometry = ViewportGeometry(
            screen_width=target_resolution[0],
            screen_height=target_resolution[1],
            window_width=target_resolution[0],
            window_height=target_resolution[1]
        )
        self.is_calibrated = False

    EXCLUDE_KEYWORDS = ["controller", "farming controller", "command prompt", "powershell", "visual studio", "gemini", "antigravity", "py_compile", "cmd.exe"]

    def is_google_play_games(self) -> bool:
        """Returns True if the connected window is Google Play Games on PC."""
        return "google play games" in self.geometry.window_title.lower()

    def calibrate_live_window(self) -> ViewportGeometry:
        """Finds the Clash of Clans / emulator window and calculates viewport geometry."""
        target_keywords = [t.strip().lower() for t in self.title_pattern.split("|") if t.strip()]
        matched_window = None

        # 1. Search via pygetwindow
        try:
            for w in gw.getAllWindows():
                w_title = w.title.strip()
                if not w_title:
                    continue
                w_lower = w_title.lower()
                if any(ex in w_lower for ex in self.EXCLUDE_KEYWORDS):
                    continue
                if any(kw in w_lower for kw in target_keywords):
                    if w.width > 200 and w.height > 200:
                        matched_window = {
                            "hwnd": getattr(w, "_hWnd", None),
                            "title": w.title,
                            "left": w.left,
                            "top": w.top,
                            "width": w.width,
                            "height": w.height
                        }
                        break
        except Exception as e:
            logger.warning(f"pygetwindow search error: {e}")

        # 2. Search via ctypes Win32 API
        if not matched_window:
            matched_window = self._find_window_ctypes(target_keywords)

        # 3. If found, query client area (excludes title bar & window borders)
        if matched_window and matched_window.get("hwnd"):
            hwnd = matched_window["hwnd"]
            user32 = ctypes.windll.user32

            crect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(crect))
            pt = wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(pt))

            client_left = pt.x
            client_top = pt.y
            client_w = crect.right
            client_h = crect.bottom

            # If client dimensions are valid, use client area
            if client_w > 200 and client_h > 200:
                win_left = client_left
                win_top = client_top
                win_w = client_w
                win_h = client_h
            else:
                win_left = matched_window.get("left", 0)
                win_top = matched_window.get("top", 0)
                win_w = matched_window.get("width", 1920)
                win_h = matched_window.get("height", 1080)

            win_title = matched_window.get("title", "")
            scale_x = win_w / float(self.target_resolution[0])
            scale_y = win_h / float(self.target_resolution[1])
            is_fs = (win_left <= 0 and win_top <= 0 and win_w >= 1900 and win_h >= 1050)

            self.geometry = ViewportGeometry(
                screen_width=self.target_resolution[0],
                screen_height=self.target_resolution[1],
                window_x=win_left,
                window_y=win_top,
                window_width=win_w,
                window_height=win_h,
                scale_x=scale_x,
                scale_y=scale_y,
                is_fullscreen=is_fs,
                confidence=0.98,
                hwnd=hwnd,
                window_title=win_title
            )
            self.is_calibrated = True
            logger.info(f"Calibrated active window client area: '{win_title}' ({win_w}x{win_h} at [{win_left},{win_top}])")
        else:
            # Fallback to primary screen
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0) or self.target_resolution[0]
            sh = user32.GetSystemMetrics(1) or self.target_resolution[1]

            self.geometry = ViewportGeometry(
                screen_width=sw,
                screen_height=sh,
                window_x=0,
                window_y=0,
                window_width=sw,
                window_height=sh,
                scale_x=sw / float(self.target_resolution[0]),
                scale_y=sh / float(self.target_resolution[1]),
                is_fullscreen=True,
                confidence=0.70,
                window_title="Primary Screen"
            )
            self.is_calibrated = True
            logger.info(f"No specific game window found. Using screen resolution ({sw}x{sh})")

        return self.geometry

    def bind_foreground_window(self) -> ViewportGeometry:
        """Binds directly to the currently active foreground window."""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return self.geometry

        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        title = buff.value.strip()
        title_lower = title.lower()
        if any(ex in title_lower for ex in self.EXCLUDE_KEYWORDS):
            logger.info(f"Ignoring foreground window '{title}' (matches dashboard/console). Searching for Clash of Clans window...")
            return self.calibrate_live_window()

        crect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(crect))
        pt = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        client_left = pt.x
        client_top = pt.y
        client_w = crect.right
        client_h = crect.bottom

        if client_w > 200 and client_h > 200:
            self.geometry = ViewportGeometry(
                screen_width=self.target_resolution[0],
                screen_height=self.target_resolution[1],
                window_x=client_left,
                window_y=client_top,
                window_width=client_w,
                window_height=client_h,
                scale_x=client_w / float(self.target_resolution[0]),
                scale_y=client_h / float(self.target_resolution[1]),
                is_fullscreen=(client_left <= 0 and client_top <= 0 and client_w >= 1900),
                confidence=1.0,
                hwnd=hwnd,
                window_title=title
            )
            self.is_calibrated = True
            logger.info(f"Explicitly bound to foreground window: '{title}' ({client_w}x{client_h} at [{client_left},{client_top}])")

        return self.geometry

    def is_game_in_foreground(self) -> bool:
        """
        Safety Guard: checks if the game window is currently the active foreground window.
        Returns True if game is focused, False if user switched to another app.
        """
        user32 = ctypes.windll.user32
        fg_hwnd = user32.GetForegroundWindow()

        # If we have a bound HWND, verify directly or via root/ancestor window
        if self.geometry.hwnd:
            if fg_hwnd == self.geometry.hwnd:
                return True
            try:
                root_fg = user32.GetAncestor(fg_hwnd, 2)  # GA_ROOT = 2
                root_geo = user32.GetAncestor(self.geometry.hwnd, 2)
                if (root_fg and root_fg == self.geometry.hwnd) or (root_geo and root_geo == fg_hwnd) or (root_fg and root_geo and root_fg == root_geo):
                    return True
            except Exception:
                pass

        # Check foreground window title
        if fg_hwnd:
            length = user32.GetWindowTextLengthW(fg_hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(fg_hwnd, buff, length + 1)
                fg_title = buff.value.lower()
                target_keywords = [t.strip().lower() for t in self.title_pattern.split("|") if t.strip()]
                if any(kw in fg_title for kw in target_keywords):
                    # Update hwnd if it's the game
                    self.geometry.hwnd = fg_hwnd
                    return True

        # If no specific game window was ever found, allow execution
        if not self.geometry.hwnd or self.geometry.window_title == "Primary Screen":
            return True

        return False

    def focus_game_window(self) -> bool:
        """Brings the game window to the foreground reliably."""
        if self.geometry.hwnd:
            try:
                hwnd = self.geometry.hwnd
                user32 = ctypes.windll.user32
                user32.keybd_event(0x12, 0, 0, 0)  # Press Alt
                user32.ShowWindow(hwnd, 9)          # SW_RESTORE
                user32.SetForegroundWindow(hwnd)    # Focus
                user32.keybd_event(0x12, 0, 2, 0)  # Release Alt
                return True
            except Exception as e:
                logger.warning(f"Failed to focus window: {e}")
        return False

    def _find_window_ctypes(self, target_keywords: List[str]) -> Optional[Dict[str, Any]]:
        user32 = ctypes.windll.user32
        matched = []

        def enum_cb(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    title_lower = title.lower()
                    if any(ex in title_lower for ex in self.EXCLUDE_KEYWORDS):
                        return 1
                    if any(kw in title_lower for kw in target_keywords):
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 200 and h > 200:
                            matched.append({
                                "hwnd": hwnd,
                                "title": title,
                                "left": rect.left,
                                "top": rect.top,
                                "width": w,
                                "height": h
                            })
            return 1

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return matched[0] if matched else None

    def normalized_to_pixel(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        pixel_x = int(self.geometry.window_x + (norm_x * self.geometry.window_width))
        pixel_y = int(self.geometry.window_y + (norm_y * self.geometry.window_height))
        return pixel_x, pixel_y

    def pixel_to_normalized(self, pixel_x: int, pixel_y: int) -> Tuple[float, float]:
        rel_x = pixel_x - self.geometry.window_x
        rel_y = pixel_y - self.geometry.window_y
        norm_x = max(0.0, min(1.0, rel_x / float(max(1, self.geometry.window_width))))
        norm_y = max(0.0, min(1.0, rel_y / float(max(1, self.geometry.window_height))))
        return norm_x, norm_y

    def get_capture_box(self) -> Dict[str, int]:
        # Dynamically track window position if user moved or resized the window
        if self.geometry.hwnd:
            try:
                user32 = ctypes.windll.user32
                crect = wintypes.RECT()
                user32.GetClientRect(self.geometry.hwnd, ctypes.byref(crect))
                pt = wintypes.POINT(0, 0)
                user32.ClientToScreen(self.geometry.hwnd, ctypes.byref(pt))
                if crect.right > 200 and crect.bottom > 200:
                    self.geometry.window_x = pt.x
                    self.geometry.window_y = pt.y
                    self.geometry.window_width = crect.right
                    self.geometry.window_height = crect.bottom
            except Exception:
                pass

        return {
            "top": max(0, self.geometry.window_y),
            "left": max(0, self.geometry.window_x),
            "width": max(100, self.geometry.window_width),
            "height": max(100, self.geometry.window_height)
        }
