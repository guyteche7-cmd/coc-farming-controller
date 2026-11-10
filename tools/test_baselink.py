import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for url in [
    'https://clashbaselink.com/th15-war-base-links/',
    'https://clashcodes.com/th15-war-bases'
]:
    print(f"Testing {url}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            urls = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|webp)', html)
            print(f"  Found {len(urls)} images")
            for u in urls[:5]:
                print("    ", u)
    except Exception as e:
        print("  Error:", e)
