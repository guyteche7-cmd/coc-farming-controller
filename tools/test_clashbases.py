import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = 'https://clashbases.de/Townhall-15'
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    print(f"Found {len(imgs)} imgs")
    for i in imgs[:10]:
        print(" ", i)
except Exception as e:
    print("Error:", e)
