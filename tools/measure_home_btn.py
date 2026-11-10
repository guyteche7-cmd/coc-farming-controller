import cv2

img = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787421682683.png")
h, w, _ = img.shape
print(f"Original screenshot size: {w}x{h}")

# The Attack button template
tmpl = cv2.imread("assets/ui/home_attack_button.png")
th, tw, _ = tmpl.shape

res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

center_x = max_loc[0] + tw // 2
center_y = max_loc[1] + th // 2

norm_x = center_x / float(w)
norm_y = center_y / float(h)

print(f"Home Attack Button: pixel=({center_x}, {center_y}), norm=({norm_x:.4f}, {norm_y:.4f}), match_score={max_val:.3f}")
