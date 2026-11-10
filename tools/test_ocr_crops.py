import cv2
from src.vision.ocr_engine import OCREngine

img_battle = cv2.imread("assets/test_cases/screen_7_active_battle.png")
h, w, _ = img_battle.shape
ocr = OCREngine()

# Bottom-right damage
dmg_crop = img_battle[int(h * 0.74):int(h * 0.83), int(w * 0.84):int(w * 0.995)]
t_dmg, _ = ocr.read_text(dmg_crop)
print(f"Raw Damage OCR text: '{t_dmg}'")

# Top-center timer
timer_crop = img_battle[int(h * 0.01):int(h * 0.08), int(w * 0.44):int(w * 0.56)]
t_timer, _ = ocr.read_text(timer_crop)
print(f"Raw Timer OCR text: '{t_timer}'")
