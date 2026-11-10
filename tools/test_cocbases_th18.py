import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for url in [
    'https://cocbases.com/th18-bases/',
    'https://cocbases.com/th18-war-bases/',
    'https://cocbases.com/tag/th18/'
]:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|webp)', html)
            print(f"{url} -> status {resp.status}, imgs {len(imgs)}")
            for i in imgs[:5]:
                print("  ", i)
    except Exception as e:
        print(f"{url} -> err {e}")
