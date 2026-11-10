import os
import cv2
import numpy as np

images = {
    "home": r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423034479.jpg",
    "attack_menu": r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423034404.jpg",
    "my_army": r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423139039.png",
    "clouds": r"C:/Users/ayush/.gemini/antigravity/brain/ee06cf55-ba4c-4e33-9044-86a7acf46bc2/.user_uploaded/media_1787423300906.png"
}

for name, path in images.items():
    img = cv2.imread(path)
    if img is not None:
        print(f"{name}: shape = {img.shape}")
    else:
        print(f"FAILED to read {name} from {path}")
