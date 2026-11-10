import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

matched = []

def enum_cb(hwnd, extra):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            crect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(crect))
            
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 50 and h > 50:
                matched.append((hwnd, title, rect.left, rect.top, w, h, crect.right, crect.bottom))
    return True

user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

print(f"Total visible windows found: {len(matched)}")
for hwnd, title, left, top, w, h, cw, ch in matched:
    print(f"HWND: {hwnd:8d} | Size: {w:4d}x{h:4d} (Client: {cw:4d}x{ch:4d}) at ({left:4d}, {top:4d}) | Title: '{title}'")
