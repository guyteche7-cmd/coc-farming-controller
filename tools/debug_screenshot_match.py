import sys, os
sys.path.insert(0, os.path.abspath("."))
import cv2
import numpy as np
from src.vision.state_detector import UIStateDetector

img = cv2.imread(r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787431936018.jpg")
coc_win = img[44:432, 4:730]

detector = UIStateDetector()
res = detector.detect_ui_state(coc_win)
print(f"Detected UI state on CoC window: {res.value} (confidence: {res.confidence:.2f})")
