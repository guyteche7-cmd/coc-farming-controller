import cv2
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.vision.ai_detector import AIVisionDetector
from src.vision.ocr_engine import OCREngine

img_path = r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787468049167.jpg"
img = cv2.imread(img_path)
h, w, _ = img.shape

ai = AIVisionDetector()
ocr = OCREngine()

dets = ai.detect(img)

for cls in ["gold", "elixir", "d_elixir"]:
    if cls in dets and dets[cls]:
        best = max(dets[cls], key=lambda x: x["confidence"])
        x1, y1, x2, y2 = best["bbox_pixel"]
        # Expand slightly right for full digits
        crop = img[max(0, y1-2):min(h, y2+2), max(0, x1-2):min(w, x2+40)]
        val, conf = ocr.read_integer(crop)
        print(f"YOLO-Guided OCR for {cls.upper()}: Value={val}, Conf={conf:.2f}")
