import os
import cv2
import numpy as np

images = {
    "home": r"assets/reference/media_1787423034479.jpg",
    "attack_menu": r"assets/reference/media_1787423034404.jpg",
    "my_army": r"assets/reference/media_1787423139039.png",
    "clouds": r"assets/reference/media_1787423300906.png"
}

for name, path in images.items():
    img = cv2.imread(path)
    if img is not None:
        print(f"{name}: shape = {img.shape}")
    else:
        print(f"FAILED to read {name} from {path}")
