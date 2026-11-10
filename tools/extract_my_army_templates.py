import cv2

img = cv2.imread(r"assets/reference/media_1787459793239.png")
h, w, _ = img.shape
print(f"Image size: {w}x{h}")

# 1. Extract green attack button on bottom right
# x: 0.76 to 0.94 -> 778 to 962
# y: 0.82 to 0.90 -> 471 to 518
btn_crop = img[470:520, 775:960]
cv2.imwrite("assets/ui/army_screen_attack_button.png", btn_crop)
print("Saved assets/ui/army_screen_attack_button.png:", btn_crop.shape)

# 2. Extract My Army tab at top
tab_crop = img[60:110, 95:370]
cv2.imwrite("assets/ui/my_army_header.png", tab_crop)
print("Saved assets/ui/my_army_header.png:", tab_crop.shape)

print("Extraction complete!")
