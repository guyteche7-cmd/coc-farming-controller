import cv2
from src.vision.ocr_engine import OCREngine

img_battle = cv2.imread("assets/test_cases/screen_7_active_battle.png")
h, w, _ = img_battle.shape
ocr = OCREngine()

dmg_crop = img_battle[int(h * 0.740):int(h * 0.830), int(w * 0.840):int(w * 0.995)]
val, conf = ocr.read_percentage(dmg_crop)
text, _ = ocr.read_text(dmg_crop)
print(f"Text: '{text}', Parsed Val: {val}, Conf: {conf}")
