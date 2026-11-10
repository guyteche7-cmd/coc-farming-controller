import urllib.request
import re
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = 'https://clashbaselink.com/th18-base-layout/'
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
        print(f"Status {resp.status}, found {len(imgs)} images on clashbaselink")
        for i in imgs[:10]:
            print(" ", i)
except Exception as e:
    print("Err:", e)
