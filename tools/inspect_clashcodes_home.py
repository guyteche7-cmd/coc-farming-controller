import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

url = "https://clashcodes.com/"
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        links = re.findall(r'href="([^"]+)"', html)
        th_links = [l for l in set(links) if 'th' in l.lower() or 'town' in l.lower()]
        print(f"ClashCodes home links: {len(links)} total, TH links: {th_links[:10]}")
except Exception as e:
    print(f"Error: {e}")
