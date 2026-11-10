import pygetwindow as gw

print("=== PyGetWindow Windows List ===")
all_wins = gw.getAllWindows()
for w in all_wins:
    if w.title.strip():
        print(f"Title: '{w.title}' | Visible: {w.visible} | Rect: ({w.left}, {w.top}, {w.width}, {w.height})")
