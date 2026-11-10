import urllib.request
import re

url = 'https://cocbases.com/th15-war-bases/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    img_urls = set(re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|webp)', html))
    print(f'Found {len(img_urls)} image URLs')
    for u in list(img_urls)[:10]:
        print(u)
except Exception as e:
    print('Error:', e)
