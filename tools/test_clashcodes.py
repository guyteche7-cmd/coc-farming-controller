import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17]:
    url = f"https://clashcodes.com/th{th}-bases"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # find upload/base images
            imgs = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|webp)', html)
            base_imgs = [i for i in set(imgs) if 'upload' in i or 'base' in i]
            print(f"TH{th} clashcodes: {len(base_imgs)} base images found")
            for b in list(base_imgs)[:5]:
                print("  ", b)
    except Exception as e:
        print(f"TH{th} clashcodes err: {e}")
