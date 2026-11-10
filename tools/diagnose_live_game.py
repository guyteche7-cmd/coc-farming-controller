import sys

if sys.platform != "win32":
    import subprocess
    print("=== macOS Diagnostics for Clash of Clans / BlueStacks ===")
    osa_script = '''
    tell application "System Events"
        set procList to every application process whose visible is true
        repeat with proc in procList
            set pName to name of proc
            try
                set winList to every window of proc
                repeat with w in winList
                    set {x, y} to position of w
                    set {w_val, h_val} to size of w
                    set wTitle to name of w
                    log (pName & " | Window: '" & wTitle & "' | Pos: (" & (x as text) & ", " & (y as text) & ") | Size: (" & (w_val as text) & ", " & (h_val as text) & ")")
                end repeat
            end try
        end repeat
    end tell
    '''
    res = subprocess.run(["osascript", "-e", osa_script], capture_output=True, text=True)
    print(res.stderr if res.stderr else res.stdout)
    sys.exit(0)

import ctypes
import ctypes.wintypes
import cv2
import numpy as np
import mss

user32 = ctypes.windll.user32

def enum_windows():
    found = []
    
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                
                crect = ctypes.wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(crect))
                
                found.append({
                    "hwnd": hwnd,
                    "title": title,
                    "rect": (rect.left, rect.top, rect.right, rect.bottom),
                    "w_h": (rect.right - rect.left, rect.bottom - rect.top),
                    "client_w_h": (crect.right, crect.bottom)
                })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return found

windows = enum_windows()
print("=== All Visible Windows with Titles ===")
for w in windows:
    t = w["title"].lower()
    if any(k in t for k in ["clash", "google play", "bluestacks", "ldplayer", "nox", "memu", "game"]):
        print(f"MATCH: HWND={w['hwnd']} | Title='{w['title']}' | Rect={w['rect']} | Size={w['w_h']} | ClientSize={w['client_w_h']}")
    elif "dashboard" in t or "coc" in t or "controller" in t:
        print(f"DASHBOARD: HWND={w['hwnd']} | Title='{w['title']}' | Rect={w['rect']}")
