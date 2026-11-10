import urllib.request
import re
import os
import cv2
import numpy as np

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

TARGET_DIR = r"C:\Users\ayush\.gemini\antigravity\scratch\coc-farming-controller\assets\downloads"
os.makedirs(TARGET_DIR, exist_ok=True)

# Function to fetch base images from ClashCodes
def get_images_from_url(url):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'/uploads/bases/[^"]+\.(?:jpg|png|webp)', html)
            full_urls = []
            for i in imgs:
                clean = i.split('?')[0]
                full_urls.append(f"https://clashcodes.com{clean}")
            return list(dict.fromkeys(full_urls))
    except Exception as e:
        print(f"Error reading {url}: {e}")
        return []

def download_and_verify(img_url, dest_path):
    try:
        req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return False, "Failed to decode"
        h, w = img.shape[:2]
        # Verify it's a real high-res full base screenshot (at least 600 width, landscape aspect)
        if w < 600 or h < 350:
            return False, f"Resolution too low ({w}x{h})"
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True, f"{w}x{h}, {len(data)} bytes"
    except Exception as e:
        return False, str(e)

for th in [15, 16, 17, 18]:
    print(f"\n==================== PROCESSING TH{th} ====================")
    # War & Legend for Max bases (competitive max-tier bases)
    max_urls = []
    max_urls.extend(get_images_from_url(f"https://clashcodes.com/bases/th{th}-war"))
    max_urls.extend(get_images_from_url(f"https://clashcodes.com/bases/th{th}-legend"))
    max_urls = list(dict.fromkeys(max_urls))

    # Farming & Hybrid for Partially Max bases (farming layout with storages spread, upgrading buildings)
    part_urls = []
    part_urls.extend(get_images_from_url(f"https://clashcodes.com/bases/th{th}-farming"))
    part_urls.extend(get_images_from_url(f"https://clashcodes.com/bases/th{th}-hybrid"))
    part_urls.extend(get_images_from_url(f"https://clashcodes.com/bases/th{th}"))
    # exclude any already in max_urls
    part_urls = [u for u in dict.fromkeys(part_urls) if u not in max_urls]

    # Download 10 Max Bases
    saved_max = 0
    for u in max_urls:
        if saved_max >= 10:
            break
        fn = f"th{th}_max_base_{saved_max + 1:02d}.jpg"
        fp = os.path.join(TARGET_DIR, fn)
        ok, msg = download_and_verify(u, fp)
        if ok:
            saved_max += 1
            print(f"  [SAVED MAX {saved_max}/10] {fn}: {msg}")
        else:
            print(f"  [SKIP MAX] {u} -> {msg}")

    # Download 10 Partially Max Bases
    saved_part = 0
    for u in part_urls:
        if saved_part >= 10:
            break
        fn = f"th{th}_partially_max_base_{saved_part + 1:02d}.jpg"
        fp = os.path.join(TARGET_DIR, fn)
        ok, msg = download_and_verify(u, fp)
        if ok:
            saved_part += 1
            print(f"  [SAVED PARTIAL {saved_part}/10] {fn}: {msg}")
        else:
            print(f"  [SKIP PARTIAL] {u} -> {msg}")

    print(f"TH{th} complete: {saved_max} Max, {saved_part} Partially Max")

print("\nALL HIGH-RES FULL SCREENSHOT DOWNLOADS COMPLETED!")
