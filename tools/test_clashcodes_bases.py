import urllib.request
import re
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for url in [
    'https://clashcodes.com/bases/th15-war',
    'https://clashcodes.com/bases/th15-farming',
    'https://clashcodes.com/bases/th16-war',
    'https://clashcodes.com/bases/th17-war',
    'https://clashcodes.com/bases/th18-war'
]:
    print(f"\nChecking {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
            upload_imgs = [i for i in imgs if 'upload' in i or 'base' in i]
            print(f"  Status {resp.status}, found {len(upload_imgs)} base images")
            if upload_imgs:
                sample_url = upload_imgs[0]
                if not sample_url.startswith('http'):
                    sample_url = f"https://clashcodes.com{sample_url}"
                print(f"  Testing sample: {sample_url}")
                s_req = urllib.request.Request(sample_url, headers=headers)
                with urllib.request.urlopen(s_req, timeout=10) as s_resp:
                    data = s_resp.read()
                    arr = np.frombuffer(data, np.uint8)
                    im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if im is not None:
                        print(f"  SUCCESS! Image shape: {im.shape}, size: {len(data)} bytes")
                    else:
                        print(f"  Decoded None")
    except Exception as e:
        print(f"  Error: {e}")
