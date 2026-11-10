import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for th in [15, 16, 17, 18]:
    for cat in ['war', 'farm']:
        url = f'https://clashofclans-layouts.com/plans/th_{th}/{cat}/'
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                pics = re.findall(r'src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
                alts = re.findall(r'alt\s*=\s*["\']([^"\']+)["\']\s+[^>]*src=["\'](/pics/th\d+_plans/[^"\']+)["\']', html)
                print(f"TH{th} {cat}: {len(pics)} pics found. With alts: {len(alts)}")
                if alts:
                    print(f"   Sample alt: {alts[0][0][:50]} -> {alts[0][1]}")
        except Exception as e:
            print(f"TH{th} {cat} error: {e}")
