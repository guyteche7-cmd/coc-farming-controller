import urllib.request
import re
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for url in [
    'https://cocbase.net/th15-war-bases/',
    'https://cocbase.net/category/th15/'
]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'src=["\'](https?://cocbase\.net/wp-content/uploads/[^"\']+)["\']', html)
            print(f"{url} -> {resp.status}, found {len(imgs)} imgs")
            for img_url in imgs[:5]:
                print("  ", img_url)
    except Exception as e:
        print(f"{url} -> {e}")
