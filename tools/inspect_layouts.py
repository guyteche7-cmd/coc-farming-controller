import urllib.request
import re
import os
import sys

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    for cat in ['war', 'farm']:
        url = f'https://clashofclans-layouts.com/plans/th_{th}/{cat}/'
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                pics = re.findall(r'src=["\'](/pics/[^"\']+)["\']', html)
                hrefs = re.findall(r'href=["\'](/pics/[^"\']+)["\']', html)
                print(f"TH{th} {cat}: {len(pics)} img tags, {len(hrefs)} hrefs. Samples: {pics[:2]} | {hrefs[:2]}")
        except Exception as e:
            print(f"TH{th} {cat} error: {e}")
