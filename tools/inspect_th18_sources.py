import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for url in [
    'https://clashcodes.com/bases/th18',
    'https://clashcodes.com/bases/th18-farming',
    'https://clashcodes.com/bases/th18-hybrid',
    'https://clashcodes.com/bases/th18-legend',
    'https://clashcodes.com/bases/th18-war'
]:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'/uploads/bases/[^"]+\.(?:jpg|png|webp)', html)
            print(f"{url}: {len(imgs)} imgs")
            for i in imgs[:5]:
                print("  ", i)
    except Exception as e:
        print(f"{url}: {e}")
