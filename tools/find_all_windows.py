import pygetwindow as gw

print("=== ALL ACTIVE OPEN WINDOWS ===")
for w in gw.getAllWindows():
    title = w.title.strip()
    if title:
        print(f"HWND: {getattr(w, '_hWnd', 'N/A')} | Size: {w.width}x{w.height} | Title: '{title}'")
