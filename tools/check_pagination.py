import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for cat in ['war', 'farm', 'defence']:
    url = f'https://clashofclans-layouts.com/plans/th_15/{cat}/'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            pages = re.findall(r'href="([^"]+)"', html)
            pagination = [p for p in set(pages) if 'page' in p]
            print(f"TH15 {cat} status {resp.status}, pagination links: {pagination}")
    except Exception as e:
        print(f"TH15 {cat} error: {e}")
