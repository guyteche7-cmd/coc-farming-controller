import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

windows = []

def enum_proc(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            windows.append((hwnd, w, h, buff.value))
    return True

user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

print(f"Found {len(windows)} visible windows:\n")
for hwnd, w, h, title in windows:
    if any(k in title.lower() for k in ["ld", "player", "clash", "google", "coc", "blue", "nox", "mumu", "farm", "cmd", "python"]):
        print(f"HWND: 0x{hwnd:08X} ({hwnd}) | Size: {w}x{h} | Title: '{title}'")
