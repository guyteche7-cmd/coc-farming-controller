import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# Test GetForegroundWindow
fg = user32.GetForegroundWindow()
length = user32.GetWindowTextLengthW(fg)
buff = ctypes.create_unicode_buffer(length + 1)
user32.GetWindowTextW(fg, buff, length + 1)
print(f"Foreground HWND: {fg} | Title: '{buff.value}'")

# Test FindWindowW with common names
for name in ["Clash of Clans", "Google Play Games", "BlueStacks", "LDPlayer", "NoxPlayer", "MuMuPlayer", "HD-Player"]:
    h = user32.FindWindowW(None, name)
    if h:
        print(f"FindWindowW exact match for '{name}': HWND={h}")
    else:
        print(f"FindWindowW no exact match for '{name}'")

# Traverse window list via GetWindow GW_HWNDNEXT
GW_HWNDNEXT = 2
hwnd = user32.GetTopWindow(user32.GetDesktopWindow())
count = 0
found_windows = []
while hwnd:
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if title:
            found_windows.append((hwnd, title, rect.left, rect.top, w, h, user32.IsWindowVisible(hwnd)))
    hwnd = user32.GetWindow(hwnd, GW_HWNDNEXT)
    count += 1

print(f"\nTraversed {count} windows in hierarchy, found {len(found_windows)} with titles:")
for hwnd, title, left, top, w, h, vis in found_windows:
    print(f"HWND: {hwnd:8d} | Vis: {vis} | {w:4d}x{h:4d} at ({left:4d}, {top:4d}) | Title: '{title}'")
