import urllib.request
import re
import os
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_DIR = r"assets\downloads"

url = 'https://clashbaselink.com/th18-base-layout/'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
overview_imgs = [i for i in imgs if 'overview' in i and ('war' in i or 'cwl' in i or 'ranked' in i)]
print(f"Found {len(overview_imgs)} TH18 overview images: {overview_imgs}")

for idx, img_url in enumerate(overview_imgs, start=4):
    if idx > 10:
        break
    fn = f"th18_max_base_{idx:02d}.jpg"
    fp = os.path.join(TARGET_DIR, fn)
    try:
        s_req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(s_req, timeout=15) as s_resp:
            data = s_resp.read()
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            # save as jpg
            cv2.imwrite(fp, img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            print(f"  [SAVED MAX TH18 {idx}/10] {fn}: {img.shape}, {os.path.getsize(fp)} bytes")
        else:
            print(f"  Failed decode for {img_url}")
    except Exception as e:
        print(f"  Error on {img_url}: {e}")
