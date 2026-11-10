import cv2
import numpy as np

img = cv2.imread(r"assets/reference/media_1787431936018.jpg")
h, w, _ = img.shape
print(f"User screenshot size: {w}x{h}")

# The CoC window client area inside this 1024x576 image:
# Left ~ 3px, Top ~ 42px, Right ~ 730px, Bottom ~ 432px
# Let's locate the CoC canvas in the screenshot
coc_win = img[44:432, 4:730]
cv2.imwrite("data/diagnostics/coc_window_sample.png", coc_win)
ch, cw, _ = coc_win.shape
print(f"Cropped CoC window size: {cw}x{ch}")

# 1. Attack button at bottom-left of CoC window
# Norm pos: x: 0.05 to 0.16, y: 0.82 to 0.98
attack_btn = coc_win[int(ch*0.82):int(ch*0.98), int(cw*0.04):int(cw*0.16)]
cv2.imwrite("assets/ui/home_attack_button.png", attack_btn)

# 2. Shop button at bottom-right of CoC window
# Norm pos: x: 0.88 to 0.99, y: 0.80 to 0.98
shop_btn = coc_win[int(ch*0.80):int(ch*0.98), int(cw*0.88):int(cw*0.99)]
cv2.imwrite("assets/ui/home_shop_button.png", shop_btn)

# 3. Builder HUD at top center of CoC window
# Norm pos: x: 0.46 to 0.55, y: 0.01 to 0.12
builder_hud = coc_win[int(ch*0.01):int(ch*0.12), int(cw*0.46):int(cw*0.55)]
cv2.imwrite("assets/ui/builder_hud.png", builder_hud)

print("Saved updated home UI templates from live window screenshot!")
